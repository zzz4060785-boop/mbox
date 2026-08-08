from flask import (
    Flask,
    current_app,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta, timezone
from functools import wraps
from html import unescape
from markupsafe import Markup, escape
from pathlib import Path
from email.message import EmailMessage
import base64
import hashlib
import json
import os
import re
import secrets
from sqlalchemy import func, or_
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

from config import Config
from pybo.i18n import SUPPORTED_LANGUAGES, get_catalog, translate
from pybo.security import init_security, rate_limit
from pybo.uploads import is_safe_upload
from pybo.notifications import send_email_code, send_sms_code
from pybo.crypto import decrypt_secret, encrypt_secret
from pybo.audit import audit_event

db = SQLAlchemy()
migrate = Migrate()
oauth = OAuth()
NOTICE_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
RECOMMENDATION_VIDEO_EXTENSIONS = {"mp4", "webm"}
RECOMMENDATION_AUDIO_EXTENSIONS = {"mp3", "m4a", "wav", "ogg"}
RECOMMENDATION_CATEGORIES = {
    "restaurant": "맛집",
    "cafe": "카페",
    "travel": "여행지",
    "stay": "숙박",
    "health": "병원·건강",
    "service": "생활서비스",
    "alumni": "동창 가게",
    "other": "기타",
}
HASHTAG_PATTERN = re.compile(r"(?<![\w&])#([0-9A-Za-z가-힣_]{1,50})")
KOREAN_INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
NEIS_SCHOOL_CACHE = {"loaded_at": None, "rows": []}
MAX_USER_SCHOOLS = 2


def _get_korean_initials(value):
    initials = []
    for character in value:
        code = ord(character) - 0xAC00
        if 0 <= code <= 11171:
            initials.append(KOREAN_INITIALS[code // 588])
        elif "ㄱ" <= character <= "ㅎ":
            initials.append(character)
    return "".join(initials)


def _extract_neis_rows(payload):
    rows = []
    for section in payload.get("schoolInfo", []):
        rows.extend(section.get("row", []))
    return rows


def _classify_uploaded_media(uploaded_file):
    """허용한 사진·영상·오디오인지 확장자와 MIME을 함께 검사합니다."""
    raw_name = Path(uploaded_file.filename or "").name
    extension = Path(raw_name).suffix.lower().lstrip(".")
    if extension in NOTICE_IMAGE_EXTENSIONS:
        media_type = "image"
    elif extension in RECOMMENDATION_VIDEO_EXTENSIONS:
        media_type = "video"
    elif extension in RECOMMENDATION_AUDIO_EXTENSIONS:
        media_type = "audio"
    else:
        return None, None, "허용되지 않는 미디어 형식입니다."
    mimetype = uploaded_file.mimetype or ""
    if not mimetype.startswith(f"{media_type}/"):
        return None, None, "파일 확장자와 실제 미디어 형식이 일치하지 않습니다."
    if not is_safe_upload(uploaded_file, extension, current_app.config):
        return None, None, "미디어 파일 내용이 올바르지 않습니다."
    return extension, media_type, None


def _save_notice_media(app, uploaded_file):
    """공지 미디어를 저장하고 주소·종류·원본명·오류를 반환합니다."""
    extension, media_type, error = _classify_uploaded_media(uploaded_file)
    if error:
        return None, None, None, error
    raw_name = Path(uploaded_file.filename or "").name
    original_name = secure_filename(raw_name) or f"media.{extension}"

    upload_directory = Path(app.config["UPLOAD_FOLDER"])
    upload_directory.mkdir(parents=True, exist_ok=True)
    saved_name = f"notice_{uuid4().hex}.{extension}"
    uploaded_file.save(upload_directory / saved_name)
    return (
        url_for("uploaded_media", filename=saved_name),
        media_type,
        original_name,
        None,
    )


def _delete_notice_image(app, image_url):
    """공지에서 제거된 이미지만 uploads 폴더 안에서 안전하게 삭제합니다."""
    if not image_url or "/uploads/" not in image_url:
        return
    upload_directory = Path(app.config["UPLOAD_FOLDER"]).resolve()
    image_path = (upload_directory / Path(image_url).name).resolve()
    if image_path.parent == upload_directory and image_path.name.startswith("notice_"):
        image_path.unlink(missing_ok=True)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("로그인이 필요합니다.")
            return redirect(url_for("main"))
        return view(*args, **kwargs)

    return wrapped_view


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    if app.config["APP_ENV"] == "production" and app.config["SECRET_KEY"] == "development-secret-key":
        raise RuntimeError("Production requires a strong SECRET_KEY environment variable.")
    if app.config.get("PAYMENT_ENABLED") and not all(
        app.config.get(key) for key in ("PORTONE_STORE_ID", "PORTONE_CHANNEL_KEY", "PORTONE_API_SECRET")
    ):
        raise RuntimeError("Enabled payments require all PortOne credentials.")
    init_security(app)
    if os.getenv("BEHIND_PROXY", "").lower() in {"1", "true", "yes"}:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
        )

    @app.before_request
    def select_interface_language():
        requested_language = request.args.get("lang", "").lower()
        if requested_language in SUPPORTED_LANGUAGES:
            session["language"] = requested_language
        elif "language" not in session:
            preferred = request.accept_languages.best_match(["ko", "en", "ja"])
            session["language"] = preferred if preferred in SUPPORTED_LANGUAGES else "ko"

    @app.url_defaults
    def auto_static_version(endpoint, values):
        """파일 수정 시간을 감지하여 정적 파일(JS, CSS) 캐시를 자동으로 강제 갱신합니다."""
        if endpoint == "static":
            filename = values.get("filename")
            if filename and "v" not in values:
                file_path = os.path.join(app.static_folder, filename)
                if os.path.isfile(file_path):
                    values["v"] = int(os.path.getmtime(file_path))

    @app.after_request
    def set_response_cache_headers(response):
        """안드로이드 웹뷰에서 HTML 페이지나 POST 결과를 캐싱하여 발생하는 ERR_CACHE_MISS를 방지합니다."""
        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = (
                "no-cache, must-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif request.path.endswith("/static/js/service-worker.js"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.context_processor
    def inject_interface_language():
        language = session.get("language", "ko")
        return {
            "current_language": language,
            "tr": lambda message: translate(message, language),
            "translation_catalog": get_catalog(language),
            "biz_info": {
                "name": app.config.get("COMPANY_NAME"),
                "owner": app.config.get("COMPANY_OWNER"),
                "biz_no": app.config.get("COMPANY_BIZ_NO"),
                "mail_order_no": app.config.get("COMPANY_MAIL_ORDER_NO"),
                "address": app.config.get("COMPANY_ADDRESS"),
                "phone": app.config.get("COMPANY_PHONE"),
                "email": app.config.get("COMPANY_EMAIL"),
                "escrow": app.config.get("COMPANY_ESCROW_INFO"),
            },
        }


    @app.get("/language/<language>")
    def set_language(language):
        if language in SUPPORTED_LANGUAGES:
            session["language"] = language
        target = request.args.get("next", "")
        parsed_target = urlparse(target)
        if not target or parsed_target.scheme or parsed_target.netloc:
            target = url_for("main")
        return redirect(target)

    @app.template_filter("hashtags")
    def linkify_hashtags(value):
        """본문의 #태그를 안전하게 이스케이프한 뒤 검색 링크로 바꿉니다."""
        safe_text = str(escape(value or ""))

        def replace_tag(match):
            tag = match.group(1)
            return (
                f'<a class="hashtag-link" '
                f'href="{url_for("tag_results", tag=tag)}">#{tag}</a>'
            )

        return Markup(HASHTAG_PATTERN.sub(replace_tag, safe_text))

    db.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)

    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get(
        "GOOGLE_CLIENT_SECRET"
    ):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={"scope": "openid email profile"},
        )

    if app.config.get("KAKAO_CLIENT_ID"):
        oauth.register(
            name="kakao",
            client_id=app.config["KAKAO_CLIENT_ID"],
            client_secret=app.config.get("KAKAO_CLIENT_SECRET", ""),
            access_token_url="https://kauth.kakao.com/oauth/token",
            authorize_url="https://kauth.kakao.com/oauth/authorize",
            api_base_url="https://kapi.kakao.com/",
            client_kwargs={
                "token_endpoint_auth_method": "client_secret_post",
            },
        )

    if app.config.get("NAVER_CLIENT_ID") and app.config.get(
        "NAVER_CLIENT_SECRET"
    ):
        oauth.register(
            name="naver",
            client_id=app.config["NAVER_CLIENT_ID"],
            client_secret=app.config["NAVER_CLIENT_SECRET"],
            access_token_url="https://nid.naver.com/oauth2.0/token",
            authorize_url="https://nid.naver.com/oauth2.0/authorize",
            api_base_url="https://openapi.naver.com/",
            client_kwargs={
                "token_endpoint_auth_method": "client_secret_post",
            },
        )

    if app.config.get("GMAIL_CLIENT_ID") and app.config.get(
        "GMAIL_CLIENT_SECRET"
    ):
        oauth.register(
            name="gmail_sender",
            client_id=app.config["GMAIL_CLIENT_ID"],
            client_secret=app.config["GMAIL_CLIENT_SECRET"],
            server_metadata_url=(
                "https://accounts.google.com/"
                ".well-known/openid-configuration"
            ),
            api_base_url="https://www.googleapis.com/",
            client_kwargs={
                "scope": (
                    "openid email "
                    "https://www.googleapis.com/auth/gmail.send"
                )
            },
        )

    from pybo import models




    from pybo.models import (
        AiImageUsage,
        AlbumComment,
        BoardAttachment,
        BoardComment,
        BoardNotice,
        BoardPost,
        BoardPostMeta,
        ClassroomMessage,
        ClassroomParticipant,
        ClassroomRoom,
        DirectMessage,
        ExecutiveApplication,
        Friendship,
        GmailCredential,
        Notification,
        OAuthAccount,
        RecommendationComment,
        RecommendationMedia,
        RecommendationPost,
        RecommendationReaction,
        SchoolLeaveLog,
        SecurityRateLimit,
        User,
        UserAlbumComment,
        UserAlbumDislike,
        UserAlbumLike,
        UserAlbumPhoto,
        UserSchool,
        VerificationChallenge,
    )

    def establish_login_session(user, permanent=True):
        session.clear()
        session["user_id"] = user.id
        session["session_version"] = user.session_version
        session.permanent = permanent
        audit_event("login_success", user_id=user.id)

    @app.before_request
    def validate_login_session_version():
        user_id = session.get("user_id")
        if not user_id:
            return None
        user = db.session.get(User, user_id)
        if not user or session.get("session_version") != user.session_version:
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify(success=False, message="로그인 세션이 만료되었습니다."), 401
        return None

    @app.before_request
    def enforce_daily_upload_limit():
        user_id = session.get("user_id")
        if not user_id or request.method not in {"POST", "PUT", "PATCH"} or not request.files:
            return None
        window_start = int(datetime.now(timezone.utc).timestamp()) // 86400 * 86400
        key_hash = hashlib.sha256(f"upload-user:{user_id}".encode()).hexdigest()
        record = SecurityRateLimit.query.filter_by(
            key_hash=key_hash, window_start=window_start
        ).with_for_update().first()
        if record is None:
            record = SecurityRateLimit(key_hash=key_hash, window_start=window_start, count=0)
            db.session.add(record)
        if record.count >= app.config["DAILY_UPLOAD_LIMIT"]:
            db.session.rollback()
            audit_event("upload_limit_exceeded", user_id=user_id)
            return jsonify(message="하루 업로드 한도를 초과했습니다."), 429
        record.count += 1
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify(message="업로드 요청을 다시 시도해 주세요."), 409
        return None

    def create_verification_challenge(purpose, code, user=None):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        VerificationChallenge.query.filter(
            or_(
                VerificationChallenge.expires_at < now,
                VerificationChallenge.consumed_at.isnot(None),
            )
        ).delete(synchronize_session=False)
        token = secrets.token_urlsafe(32)
        challenge = VerificationChallenge(
            token=token,
            purpose=purpose,
            user_id=user.id if user else None,
            code_hash=generate_password_hash(code),
            expires_at=now + timedelta(minutes=10),
        )
        db.session.add(challenge)
        db.session.commit()
        session[f"verification_{purpose}"] = token
        return challenge

    def verify_challenge(purpose, code, consume=True):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        token = session.get(f"verification_{purpose}")
        if not token:
            return None
        challenge = VerificationChallenge.query.filter_by(
            token=token, purpose=purpose
        ).with_for_update().first()
        if (
            not challenge
            or challenge.consumed_at is not None
            or challenge.expires_at < now
            or challenge.attempts >= 5
        ):
            session.pop(f"verification_{purpose}", None)
            db.session.rollback()
            return None
        challenge.attempts += 1
        if not check_password_hash(challenge.code_hash, code):
            db.session.commit()
            return None
        if consume:
            challenge.consumed_at = now
            session.pop(f"verification_{purpose}", None)
        db.session.commit()
        return challenge

    def add_notification(user_id, kind, title, message, target_url, actor_id=None):
        """자기 자신을 제외한 대상 사용자에게 읽지 않은 알림을 추가합니다."""
        if not user_id or user_id == actor_id:
            return
        db.session.add(
            Notification(
                user_id=user_id,
                actor_id=actor_id,
                kind=kind,
                title=title[:120],
                message=message[:300],
                target_url=target_url[:500],
            )
        )

    def notify_school_members(school_name, actor, kind, title, message, target_url):
        """새 소식(게시글, 공지사항, 사랑별 장소 등)을 같은 학교에 등록된 다른 회원들에게 알립니다."""
        if not school_name or not actor:
            return

        member_rows = (
            db.session.query(User.id)
            .outerjoin(
                UserSchool,
                UserSchool.user_id == User.id,
            )
            .filter(
                or_(
                    User.school_name == school_name,
                    UserSchool.school_name == school_name,
                )
            )
            .distinct()
            .all()
        )

        for (user_id,) in member_rows:
            if user_id != actor.id:
                add_notification(
                    user_id,
                    kind,
                    title,
                    message,
                    target_url,
                    actor.id,
                )

    def get_login_destination_url(user):
        if user:
            user.last_login_at = datetime.utcnow()
            user.last_active_at = datetime.utcnow()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

        if user and user.school_name:
            return url_for(
                "main_album",
                school=user.school_name,
                type=user.school_type,
                year=user.school_year,
                major=user.school_major or None,
            )
        return url_for("main_success")

    def login_destination(user):
        return redirect(get_login_destination_url(user), code=303)

    def remember_login_id(response, login_id, should_remember):
        """로그인 상태 유지 선택에 따라 마지막 아이디 쿠키를 관리합니다."""
        cookie_name = "friendary_login_id"

        if should_remember:
            max_age = int(
                app.config["PERMANENT_SESSION_LIFETIME"].total_seconds()
            )
            response.set_cookie(
                cookie_name,
                login_id,
                max_age=max_age,
                httponly=True,
                samesite="Lax",
                secure=app.config["SESSION_COOKIE_SECURE"],
            )
        else:
            response.delete_cookie(
                cookie_name,
                httponly=True,
                samesite="Lax",
                secure=app.config["SESSION_COOKIE_SECURE"],
            )

        return response

    from pybo.views.album_views import bp as album_bp
    from pybo.views.payment_views import bp as payment_bp

    app.register_blueprint(album_bp)
    app.register_blueprint(payment_bp)


    @app.route("/", methods=["GET", "POST"])
    @rate_limit(limit=10, window=300, scope="login-main")
    def main():
        if request.method == "GET" and session.get("user_id"):
            return login_destination(
                db.session.get(User, session["user_id"])
            )

        if request.method == "POST":
            is_ajax = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.is_json
                or "application/json" in request.headers.get("Accept", "")
            )

            if request.is_json:
                data = request.get_json() or {}
                login_id = str(data.get("login", "")).strip()
                password = str(data.get("password", ""))
                should_remember = bool(data.get("remember"))
            else:
                login_id = request.form.get("login", "").strip()
                password = request.form.get("password", "")
                should_remember = request.form.get("remember") == "on"

            user = User.query.filter(
                or_(User.username == login_id, User.email == login_id)
            ).first()

            if not user or not check_password_hash(user.password, password):
                audit_event("login_failure", {"login_hash": secrets.token_hex(8)})
                if is_ajax:
                    return jsonify(success=False, message="아이디 또는 비밀번호를 확인해 주세요."), 400
                flash("아이디 또는 비밀번호를 확인해 주세요.")
                return redirect(url_for("main"), code=303)

            establish_login_session(user, permanent=should_remember)

            dest_url = get_login_destination_url(user)
            if is_ajax:
                resp = jsonify(success=True, redirect_url=dest_url)
                return remember_login_id(resp, login_id, should_remember)

            return remember_login_id(
                redirect(dest_url, code=303),
                login_id,
                should_remember,
            )

        return render_template(
            "main.html",
            saved_login_id=request.cookies.get("friendary_login_id", ""),
        )

    @app.route("/privacy")
    @app.route("/privacy-policy")
    @app.route("/privacy_policy")
    def privacy_policy():
        return render_template("privacy_policy.html")

    @app.route("/terms")
    @app.route("/terms-of-service")
    @app.route("/terms_of_service")
    def terms_of_service():
        return render_template("terms_of_service.html")

    @app.get("/account-deletion")
    def account_deletion():
        return render_template("account_deletion.html")

    @app.get("/.well-known/assetlinks.json")
    @app.get("/assetlinks.json")
    def assetlinks():
        assetlinks_dir = os.path.join(app.static_folder, ".well-known")
        return send_from_directory(assetlinks_dir, "assetlinks.json", mimetype="application/json")

    @app.get("/service-worker.js")
    def service_worker():
        response = send_from_directory(
            os.path.join(app.static_folder, "js"),
            "service-worker.js",
            mimetype="application/javascript",
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.get("/manifest.webmanifest")
    def webmanifest():
        return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")

    @app.get("/media/<path:filename>")
    @login_required
    def uploaded_media(filename):
        safe_name = secure_filename(Path(filename).name)
        if not safe_name or safe_name != filename:
            return "Not found", 404
        response = send_from_directory(app.config["UPLOAD_FOLDER"], safe_name)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        response.headers["Cache-Control"] = "private, max-age=3600"
        return response

    @app.route("/login2", methods=["GET", "POST"])
    @rate_limit(limit=10, window=300, scope="login-secondary")
    def login2():
        if request.method == "GET" and session.get("user_id"):
            return login_destination(
                db.session.get(User, session["user_id"])
            )

        if request.method == "POST":
            is_ajax = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.is_json
                or "application/json" in request.headers.get("Accept", "")
            )

            if request.is_json:
                data = request.get_json() or {}
                login_id = str(data.get("login_id", "")).strip()
                password = str(data.get("password", ""))
                should_remember = bool(data.get("save_info"))
            else:
                login_id = request.form.get("login_id", "").strip()
                password = request.form.get("password", "")
                should_remember = request.form.get("save_info") == "on"

            user = User.query.filter(
                or_(User.username == login_id, User.email == login_id)
            ).first()

            if not user or not check_password_hash(user.password, password):
                audit_event("login_failure", {"login_hash": secrets.token_hex(8)})
                if is_ajax:
                    return jsonify(success=False, message="아이디 또는 비밀번호를 확인해 주세요."), 400
                flash("아이디 또는 비밀번호를 확인해 주세요.")
                return redirect(url_for("login2"), code=303)

            establish_login_session(user, permanent=should_remember)

            dest_url = get_login_destination_url(user)
            if is_ajax:
                resp = jsonify(success=True, redirect_url=dest_url)
                return remember_login_id(resp, login_id, should_remember)

            return remember_login_id(
                redirect(dest_url, code=303),
                login_id,
                should_remember,
            )

        return render_template(
            "login2.html",
            saved_login_id=request.cookies.get("friendary_login_id", ""),
        )

    @app.route("/main-success")
    @login_required
    def main_success():
        return render_template("main_success.html")

    @app.route("/school-find")
    @login_required
    def school_find():
        return render_template("school_find.html")

    @app.get("/api/schools/search")
    @login_required
    def search_schools():
        keyword = request.args.get("q", "").strip()
        requested_type = request.args.get("type", "").strip()
        lang = session.get("language", "ko")
        if len(keyword) < 2:
            return jsonify(schools=[])

        from pybo.japan_schools import search_japan_schools
        from pybo.us_schools import search_us_schools

        jp_schools = search_japan_schools(keyword, requested_type)
        us_schools = search_us_schools(keyword, requested_type)

        if jp_schools and (lang == "ja" or re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", keyword)):
            return jsonify(schools=jp_schools)

        if us_schools and (lang == "en" or re.search(r"[a-zA-Z]", keyword)):
            return jsonify(schools=us_schools)

        if requested_type in {"대학교", "大学"}:
            univ_api_key = app.config.get("UNIVERSITY_API_KEY", "").strip()
            career_schools = []
            if univ_api_key:
                try:
                    request_url = (
                        "https://www.career.go.kr/cnet/openapi/getOpenApi?"
                        + urlencode(
                            {
                                "apiKey": univ_api_key,
                                "svcType": "api",
                                "svcCode": "SCHOOL",
                                "contentType": "json",
                                "gubun": "univ_list",
                                "searchSchulNm": keyword,
                            }
                        )
                    )
                    career_request = Request(
                        request_url,
                        headers={"User-Agent": "Friendary/1.0"},
                    )
                    with urlopen(career_request, timeout=5) as response:
                        payload = json.loads(response.read().decode("utf-8"))

                    rows = payload.get("dataSearch", {}).get("content", [])
                    seen = set()
                    for row in rows:
                        raw_name = str(row.get("schoolName", "")).strip()
                        if not raw_name:
                            continue
                        campus = str(row.get("campusName", "")).strip()
                        full_name = (
                            f"{raw_name} ({campus})"
                            if campus and campus not in {"본교", "본교(주)"}
                            else raw_name
                        )
                        if full_name in seen:
                            continue
                        seen.add(full_name)
                        career_schools.append(
                            {
                                "name": full_name,
                                "type": "대학교",
                                "code": str(row.get("seq", "")),
                                "office_code": "",
                                "address": str(row.get("adres") or row.get("region") or ""),
                            }
                        )
                        if len(career_schools) >= 30:
                            break
                except Exception:
                    pass

            combined_schools = jp_schools + career_schools
            return jsonify(schools=combined_schools[:30])

        api_key = app.config.get("NEIS_API_KEY", "").strip()
        if not api_key:
            return jsonify(error="NEIS_API_KEY가 설정되지 않았습니다."), 503

        is_initial_search = bool(re.fullmatch(r"[ㄱ-ㅎ]+", keyword))
        try:
            if is_initial_search:
                loaded_at = NEIS_SCHOOL_CACHE["loaded_at"]
                cache_is_stale = (
                    not loaded_at
                    or datetime.utcnow() - loaded_at > timedelta(hours=24)
                )
                if cache_is_stale:
                    cached_rows = []
                    for page_index in range(1, 30):
                        request_url = (
                            "https://open.neis.go.kr/hub/schoolInfo?"
                            + urlencode(
                                {
                                    "KEY": api_key,
                                    "Type": "json",
                                    "pIndex": page_index,
                                    "pSize": 1000,
                                }
                            )
                        )
                        neis_request = Request(
                            request_url,
                            headers={"User-Agent": "Friendary/1.0"},
                        )
                        with urlopen(neis_request, timeout=10) as response:
                            page_payload = json.loads(
                                response.read().decode("utf-8")
                            )
                        page_rows = _extract_neis_rows(page_payload)
                        cached_rows.extend(page_rows)
                        if len(page_rows) < 1000:
                            break
                    NEIS_SCHOOL_CACHE["rows"] = cached_rows
                    NEIS_SCHOOL_CACHE["loaded_at"] = datetime.utcnow()

                rows = [
                    row
                    for row in NEIS_SCHOOL_CACHE["rows"]
                    if keyword in _get_korean_initials(row.get("SCHUL_NM", ""))
                ]
            else:
                request_url = (
                    "https://open.neis.go.kr/hub/schoolInfo?"
                    + urlencode(
                        {
                            "KEY": api_key,
                            "Type": "json",
                            "pIndex": 1,
                            "pSize": 30,
                            "SCHUL_NM": keyword,
                        }
                    )
                )
                neis_request = Request(
                    request_url,
                    headers={"User-Agent": "Friendary/1.0"},
                )
                with urlopen(neis_request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                rows = _extract_neis_rows(payload)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return jsonify(error="학교정보 서비스에 연결하지 못했습니다."), 502

        filterable_types = {"초등학교", "중학교", "고등학교"}
        schools = []
        seen = set()
        for row in rows:
            school_type = row.get("SCHUL_KND_SC_NM", "")
            if requested_type in filterable_types and school_type != requested_type:
                continue
            identity = (
                row.get("ATPT_OFCDC_SC_CODE", ""),
                row.get("SD_SCHUL_CODE", ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            schools.append(
                {
                    "name": row.get("SCHUL_NM", ""),
                    "type": school_type,
                    "code": identity[1],
                    "office_code": identity[0],
                    "address": row.get("ORG_RDNMA", ""),
                }
            )
            if len(schools) >= 30:
                break

        return jsonify(schools=schools)

    @app.post("/school-selection")
    @login_required
    def save_school_selection():
        data = request.get_json(silent=True) or {}
        school_name = str(data.get("school", "")).strip()
        school_type = str(data.get("type", "")).strip()
        school_year = str(data.get("year", "")).strip()
        school_major = str(data.get("major", "")).strip()

        if not school_name or not school_type or not school_year:
            return {
                "error": "학교명, 학교 구분, 연도를 모두 선택해 주세요."
            }, 400

        user = db.session.get(User, session["user_id"])
        if not user:
            session.clear()
            return {"error": "로그인이 필요합니다."}, 401

        membership = UserSchool.query.filter_by(
            user_id=user.id, school_name=school_name
        ).first()
        if (
            not membership
            and UserSchool.query.filter_by(user_id=user.id).count()
            >= MAX_USER_SCHOOLS
        ):
            return {
                "error": f"학교는 최대 {MAX_USER_SCHOOLS}개까지만 등록할 수 있어 더 이상 추가할 수 없습니다."
            }, 400
        if not membership:
            membership = UserSchool(
                user_id=user.id,
                school_name=school_name[:120],
                school_type=school_type[:30],
                school_year=school_year[:4],
                school_major=school_major[:100] or None,
                is_primary=UserSchool.query.filter_by(user_id=user.id).count() == 0,
            )
            db.session.add(membership)
        else:
            membership.school_type = school_type[:30]
            membership.school_year = school_year[:4]
            membership.school_major = school_major[:100] or None

        # 기존 단일 학교 필드는 첫 번째(대표) 학교와 계속 호환합니다.
        if not user.school_name or membership.is_primary:
            user.school_name = membership.school_name
            user.school_type = membership.school_type
            user.school_year = membership.school_year
            user.school_major = membership.school_major
        db.session.commit()

        return {
            "redirect_url": url_for(
                "main_album",
                school=membership.school_name,
                type=membership.school_type,
                year=membership.school_year,
                major=membership.school_major,
            )
        }

    @app.get("/api/my-schools")
    @login_required
    def my_schools():
        user_id = session["user_id"]
        month_key = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m")
        memberships = UserSchool.query.filter_by(user_id=user_id).order_by(
            UserSchool.is_primary.desc(), UserSchool.create_date
        ).all()
        used = SchoolLeaveLog.query.filter_by(
            user_id=user_id, month_key=month_key
        ).count()
        return jsonify(
            schools=[
                {
                    "id": item.id,
                    "school_name": item.school_name,
                    "school_type": item.school_type,
                    "school_year": item.school_year,
                    "is_primary": item.is_primary,
                    "url": url_for("main_album", school=item.school_name),
                }
                for item in memberships
            ],
            limit=MAX_USER_SCHOOLS,
            leave_used=used,
            leave_remaining=max(2 - used, 0),
        )

    def _remove_uploaded_file(file_url):
        if not file_url:
            return
        for directory in (
            Path(app.config["UPLOAD_FOLDER"]),
            Path(app.static_folder) / "uploads",  # legacy files
        ):
            upload_directory = directory.resolve()
            file_path = (upload_directory / Path(file_url).name).resolve()
            if file_path.parent == upload_directory:
                file_path.unlink(missing_ok=True)

    @app.delete("/api/my-schools/<int:membership_id>")
    @login_required
    def leave_school(membership_id):
        membership = db.get_or_404(UserSchool, membership_id)
        if membership.user_id != session["user_id"]:
            return jsonify(message="본인의 등록 학교만 삭제할 수 있습니다."), 403
        month_key = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m")
        used = SchoolLeaveLog.query.filter_by(
            user_id=membership.user_id, month_key=month_key
        ).count()
        if used >= 2:
            return jsonify(message="학교 삭제는 한 달에 최대 2회까지만 가능합니다."), 429

        user_id = membership.user_id
        school_name = membership.school_name
        board_posts = BoardPost.query.filter_by(
            user_id=user_id, school_name=school_name
        ).all()
        for post in board_posts:
            for attachment in BoardAttachment.query.filter_by(post_id=post.id).all():
                _remove_uploaded_file(attachment.file_url)
            BoardAttachment.query.filter_by(post_id=post.id).delete()
            BoardPostMeta.query.filter_by(post_id=post.id).delete()
            db.session.delete(post)
        BoardComment.query.filter_by(
            user_id=user_id, school_name=school_name
        ).delete(synchronize_session=False)

        recommendation_posts = RecommendationPost.query.filter_by(
            user_id=user_id, school_name=school_name
        ).all()
        for post in recommendation_posts:
            for media in post.media:
                _remove_uploaded_file(media.file_url)
            db.session.delete(post)
        RecommendationComment.query.filter_by(
            user_id=user_id, school_name=school_name
        ).delete(synchronize_session=False)

        album_photos = UserAlbumPhoto.query.filter_by(
            user_id=user_id, school_name=school_name
        ).all()
        for photo in album_photos:
            _remove_uploaded_file(photo.image_url)
            db.session.delete(photo)
        UserAlbumComment.query.filter_by(
            user_id=user_id, school_name=school_name
        ).delete(synchronize_session=False)
        ExecutiveApplication.query.filter_by(
            user_id=user_id, school_name=school_name
        ).delete(synchronize_session=False)

        db.session.add(
            SchoolLeaveLog(
                user_id=user_id,
                school_name=school_name,
                month_key=month_key,
            )
        )
        was_primary = membership.is_primary
        db.session.delete(membership)
        db.session.flush()
        remaining = UserSchool.query.filter_by(user_id=user_id).order_by(
            UserSchool.create_date
        ).first()
        user = db.session.get(User, user_id)
        if user.is_executive and user.school_name == school_name:
            user.is_executive = False
            user.executive_elected_at = None
        if was_primary:
            if remaining:
                remaining.is_primary = True
                user.school_name = remaining.school_name
                user.school_type = remaining.school_type
                user.school_year = remaining.school_year
                user.school_major = remaining.school_major
            else:
                user.school_name = None
                user.school_type = None
                user.school_year = None
                user.school_major = None
        db.session.commit()
        return jsonify(
            message=f"{school_name}에서 탈퇴했으며 해당 학교 작성 자료와 앨범이 모두 삭제되었습니다.",
            redirect_url=(
                url_for("main_album", school=remaining.school_name)
                if remaining
                else url_for("school_find")
            ),
            leave_remaining=max(2 - (used + 1), 0),
        )

    @app.route("/main-album")
    @login_required
    def main_album():
        user = db.session.get(User, session["user_id"])
        return render_template("main_album.html", current_user=user)

    @app.route("/star")
    @login_required
    def star_page():
        user = db.session.get(User, session["user_id"])
        return render_template("star.html", current_user=user)

    @app.route("/my-home")
    @login_required
    def my_home():
        user = db.session.get(User, session["user_id"])
        return render_template("my_home.html", current_user=user)

    @app.route("/game-zone")
    @login_required
    def game_zone():
        flash("GAME ZONE은 현재 접근할 수 없습니다.")
        return redirect(url_for("main_album"))

    @app.get("/foreign-friends")
    @login_required
    def foreign_friends():
        nationality = request.args.get("nationality", "").strip()
        age = request.args.get("age", type=int)
        gender = request.args.get("gender", "").strip()
        hobby = request.args.get("hobby", "").strip()
        searched = any((nationality, age, gender, hobby))
        users = []

        if searched:
            query = User.query.filter(
                User.id != session["user_id"],
                User.nationality.isnot(None),
                User.nationality != "",
                User.is_profile_public.is_(True),
                User.allow_friend_search.is_(True),
            )
            if nationality:
                query = query.filter(
                    User.nationality.ilike(f"%{nationality}%")
                )
            if age:
                query = query.filter(User.age == age)
            if gender in {"male", "female", "other"}:
                query = query.filter(User.gender == gender)
            if hobby:
                query = query.filter(User.hobby.ilike(f"%{hobby}%"))
            users = query.order_by(User.username.asc()).limit(50).all()

        return render_template(
            "foreign_friends.html",
            users=users,
            searched=searched,
            filters={
                "nationality": nationality,
                "age": age or "",
                "gender": gender,
                "hobby": hobby,
            },
        )

    def can_connect_admin_gmail(user):
        return bool(
            user
            and (
                user.is_executive
                or user.id in app.config.get("EXECUTIVE_USER_IDS", [])
            )
        )

    @app.get("/contact-admin")
    @login_required
    def contact_admin():
        user = db.session.get(User, session["user_id"])
        gmail_connected = GmailCredential.query.filter_by(
            email=app.config["GMAIL_ADMIN_EMAIL"]
        ).first() is not None
        return render_template(
            "contact_admin.html",
            current_user=user,
            admin_email="junyoungkim355@gmail.com",
            gmail_connected=gmail_connected,
            can_connect_gmail=can_connect_admin_gmail(user),
        )

    @app.get("/google/gmail/connect")
    @login_required
    def gmail_connect():
        user = db.session.get(User, session["user_id"])
        if not can_connect_admin_gmail(user):
            flash("관리자만 Gmail 발송 계정을 연결할 수 있습니다.")
            return redirect(url_for("contact_admin"))
        client = oauth.create_client("gmail_sender")
        if client is None:
            flash("Gmail OAuth 환경변수를 확인해 주세요.")
            return redirect(url_for("contact_admin"))
        return client.authorize_redirect(
            app.config["GMAIL_REDIRECT_URI"],
            access_type="offline",
            prompt="consent",
        )

    @app.get("/google/gmail/callback")
    @login_required
    def gmail_callback():
        user = db.session.get(User, session["user_id"])
        if not can_connect_admin_gmail(user):
            return redirect(url_for("contact_admin"))
        client = oauth.create_client("gmail_sender")
        try:
            token = client.authorize_access_token()
            userinfo_request = Request(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={
                    "Authorization": f"Bearer {token['access_token']}"
                },
            )
            with urlopen(userinfo_request, timeout=15) as response:
                account_email = json.loads(response.read()).get(
                    "email", ""
                ).lower()
        except Exception as error:
            app.logger.exception("Gmail OAuth callback failed: %s", error)
            flash("Google Gmail 인증에 실패했습니다.")
            return redirect(url_for("contact_admin"))

        admin_email = app.config["GMAIL_ADMIN_EMAIL"].lower()
        refresh_token = token.get("refresh_token")
        if account_email != admin_email:
            flash(f"{admin_email} 계정으로 승인해 주세요.")
            return redirect(url_for("contact_admin"))
        if not refresh_token:
            flash("갱신 토큰을 받지 못했습니다. 다시 연결해 주세요.")
            return redirect(url_for("contact_admin"))

        credential = GmailCredential.query.filter_by(
            email=admin_email
        ).first()
        if credential:
            credential.refresh_token = encrypt_secret(app.config, refresh_token)
        else:
            db.session.add(
                GmailCredential(
                    email=admin_email,
                    refresh_token=encrypt_secret(app.config, refresh_token),
                )
            )
        db.session.commit()
        flash("관리자 Gmail 발송 계정이 연결되었습니다.")
        return redirect(url_for("contact_admin"))

    @app.post("/api/contact-admin")
    @login_required
    def contact_admin_send():
        data = request.get_json(silent=True) or {}
        subject = str(data.get("subject", "")).strip()[:120]
        message_text = str(data.get("message", "")).strip()[:3000]
        if not subject or not message_text:
            return jsonify(message="제목과 문의 내용을 입력해 주세요."), 400

        admin_email = app.config["GMAIL_ADMIN_EMAIL"].lower()
        credential = GmailCredential.query.filter_by(email=admin_email).first()
        if not credential:
            return jsonify(
                message="관리자 Gmail 계정 연결이 아직 완료되지 않았습니다."
            ), 503

        token_request = Request(
            "https://oauth2.googleapis.com/token",
            data=urlencode(
                {
                    "client_id": app.config["GMAIL_CLIENT_ID"],
                    "client_secret": app.config["GMAIL_CLIENT_SECRET"],
                    "refresh_token": decrypt_secret(app.config, credential.refresh_token),
                    "grant_type": "refresh_token",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(token_request, timeout=15) as response:
                access_token = json.loads(response.read())["access_token"]

            sender = db.session.get(User, session["user_id"])
            email_message = EmailMessage()
            email_message["To"] = admin_email
            email_message["From"] = admin_email
            email_message["Reply-To"] = sender.email
            email_message["Subject"] = subject
            email_message.set_content(
                f"{message_text}\n\n--------------------\n"
                f"보낸 회원: {sender.username}\n회원 이메일: {sender.email}"
            )
            raw_message = base64.urlsafe_b64encode(
                email_message.as_bytes()
            ).decode("ascii")
            send_request = Request(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                data=json.dumps({"raw": raw_message}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(send_request, timeout=15):
                pass
        except HTTPError as error:
            try:
                error_data = json.loads(error.read().decode("utf-8"))
                reason = str(
                    error_data.get("error", {}).get("status")
                    or error_data.get("error")
                )[:80]
            except (ValueError, AttributeError, UnicodeDecodeError):
                reason = "http_error"
            app.logger.warning(
                "Gmail send failed: status=%s reason=%s",
                error.code,
                reason,
            )
            return jsonify(message="Gmail 인증 또는 전송에 실패했습니다."), 502
        except (URLError, KeyError, ValueError) as error:
            app.logger.warning("Gmail send failed: %s", type(error).__name__)
            return jsonify(message="Gmail 전송 서버에 연결하지 못했습니다."), 502

        return jsonify(message="관리자에게 이메일을 보냈습니다.")

    @app.route("/hogu-shop")
    @login_required
    def hogu_shop():
        flash("아바타샵은 현재 접근할 수 없습니다.")
        return redirect(url_for("my_home"))

    def _friendship_between(first_user_id, second_user_id):
        return Friendship.query.filter(
            or_(
                (
                    (Friendship.requester_id == first_user_id)
                    & (Friendship.receiver_id == second_user_id)
                ),
                (
                    (Friendship.requester_id == second_user_id)
                    & (Friendship.receiver_id == first_user_id)
                ),
            )
        ).first()

    def _relationship_data(current_user_id, other_user_id):
        """화면에 표시할 1촌 관계 상태와 자연스러운 안내 문구입니다."""
        if current_user_id == other_user_id:
            return {"status": "self", "label": "내 프로필입니다"}
        friendship = _friendship_between(current_user_id, other_user_id)
        if not friendship:
            return {
                "status": "none",
                "label": "아직 1촌이 아닙니다. 먼저 반가운 인사를 건네보세요.",
            }
        if friendship.status == "accepted":
            return {
                "status": "accepted",
                "label": "서로의 추억을 나누는 1촌 사이입니다 ✨",
                "friendship_id": friendship.id,
            }
        if friendship.requester_id == current_user_id:
            return {
                "status": "sent",
                "label": "1촌 신청을 보냈습니다. 상대의 답변을 기다리는 중이에요.",
                "friendship_id": friendship.id,
            }
        return {
            "status": "received",
            "label": "나에게 도착한 1촌 신청이 있습니다.",
            "friendship_id": friendship.id,
        }

    def _accepted_connections(user_id):
        """특정 사용자의 공개 1촌 목록을 사용자 객체 배열로 반환합니다."""
        friendships = Friendship.query.filter(
            Friendship.status == "accepted",
            or_(
                Friendship.requester_id == user_id,
                Friendship.receiver_id == user_id,
            ),
        ).order_by(Friendship.accepted_date.desc()).all()
        return [
            friendship.receiver
            if friendship.requester_id == user_id
            else friendship.requester
            for friendship in friendships
        ]

    def _visible_connections(user_id, viewer_id):
        """인맥 경유 노출과 전체 공개를 허용한 1촌만 반환합니다."""
        return [
            connection
            for connection in _accepted_connections(user_id)
            if connection.id == viewer_id
            or (
                connection.is_profile_public
                and connection.allow_connection_discovery
            )
        ]

    @app.get("/api/social/settings")
    @login_required
    def social_settings_get():
        user = db.session.get(User, session["user_id"])
        return jsonify(
            profile={
                "username": user.username,
                "school_name": user.school_name or "",
                "school_year": user.school_year or "",
                "age": user.age,
                "gender": user.gender or "",
                "nationality": user.nationality or "",
                "hobby": user.hobby or "",
            },
            settings={
                "tag_permission": user.tag_permission,
                "allow_album_comments": user.allow_album_comments,
                "allow_connection_discovery": user.allow_connection_discovery,
                "allow_messages": user.allow_messages,
                "is_profile_public": user.is_profile_public,
                "allow_friend_search": user.allow_friend_search,
            }
        )

    @app.post("/api/social/settings")
    @login_required
    def social_settings_save():
        """개인정보 설정은 로그인한 본인 계정에만 저장합니다."""
        data = request.get_json(silent=True) or {}
        user = db.session.get(User, session["user_id"])
        username = str(data.get("username", user.username)).strip()
        if len(username) < 2:
            return jsonify(message="이름은 2자 이상 입력해 주세요."), 400
        if len(username) > 50:
            return jsonify(message="이름은 50자 이하로 입력해 주세요."), 400
        tag_permission = data.get("tag_permission", "friends")
        if tag_permission not in {"friends", "off"}:
            return jsonify(message="태그 설정값을 확인해 주세요."), 400
        age_value = data.get("age")
        if age_value in ("", None):
            age = None
        else:
            try:
                age = int(age_value)
            except (TypeError, ValueError):
                return jsonify(message="나이는 숫자로 입력해 주세요."), 400
            if age < 1 or age > 120:
                return jsonify(message="나이는 1세부터 120세까지 입력할 수 있습니다."), 400
        gender = str(data.get("gender", "")).strip()
        if gender not in {"", "male", "female", "other"}:
            return jsonify(message="성별 설정값을 확인해 주세요."), 400
        user.username = username
        user.school_name = str(data.get("school_name", "")).strip()[:120] or None
        user.school_year = str(data.get("school_year", "")).strip()[:4] or None
        user.age = age
        user.gender = gender or None
        user.nationality = (
            str(data.get("nationality", "")).strip()[:80] or None
        )
        user.hobby = str(data.get("hobby", "")).strip()[:200] or None
        user.tag_permission = tag_permission
        user.allow_album_comments = bool(data.get("allow_album_comments"))
        user.allow_connection_discovery = bool(
            data.get("allow_connection_discovery")
        )
        user.allow_messages = bool(data.get("allow_messages"))
        user.is_profile_public = bool(data.get("is_profile_public"))
        user.allow_friend_search = bool(data.get("allow_friend_search"))
        db.session.commit()
        return jsonify(
            message="이름과 개인정보 설정이 저장되었습니다.",
            username=user.username,
        )

    def _get_or_grant_user_sarangdal(user, persist=True):
        """
        모든 유저에게 기본 1개를 제공하고, 매달 1일마다 1개씩 누적 자동 충전합니다.
        """
        if not user:
            return 0
        current_month = datetime.utcnow().strftime("%Y-%m")
        last_month = getattr(user, "last_sarangdal_month", None)

        if not last_month:
            if (user.sarangdal_balance or 0) < 1:
                user.sarangdal_balance = 1
            user.last_sarangdal_month = current_month
            if persist:
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
        elif last_month != current_month:
            user.sarangdal_balance = (user.sarangdal_balance or 0) + 1
            user.last_sarangdal_month = current_month
            if persist:
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        return user.sarangdal_balance or 0

    @app.get("/api/sarangdal/status")
    @login_required
    def user_sarangdal_status():
        # Serialize the monthly grant so simultaneous status/feed requests can
        # never issue the same month's free allowance twice.
        user = User.query.filter_by(id=session["user_id"]).with_for_update().first()
        if not user:
            return jsonify(error="로그인이 필요합니다."), 401
        balance = _get_or_grant_user_sarangdal(user)

        # 사용자가 남들에게 선물한 총 사랑달 개수
        total_given = UserAlbumLike.query.filter_by(user_id=user.id).count()

        # 사용자 사진이 남들에게 받은 총 사랑달 개수
        total_received = (
            UserAlbumLike.query.join(UserAlbumPhoto)
            .filter(UserAlbumPhoto.user_id == user.id)
            .count()
        )

        return jsonify(
            username=user.username,
            current_balance=balance,
            total_given=total_given,
            total_received=total_received,
            last_month=user.last_sarangdal_month or datetime.utcnow().strftime("%Y-%m"),
            monthly_free_allowance=1,
            purchased_balance_carries_over=True,
        )

    @app.get("/api/album/feed")
    @login_required
    def user_album_feed():
        current_user_id = session["user_id"]
        current_user = db.session.get(User, current_user_id)
        user_sarangdal = _get_or_grant_user_sarangdal(current_user)
        owner_id = request.args.get("user_id", type=int) or current_user_id
        query = UserAlbumPhoto.query
        if owner_id:
            owner = db.get_or_404(User, owner_id)
            if owner.id != current_user_id and not owner.is_profile_public:
                return jsonify(message="이 사용자는 프로필과 앨범을 비공개로 설정했습니다."), 403
            query = query.filter(UserAlbumPhoto.user_id == owner_id)
        photos = query.order_by(UserAlbumPhoto.create_date.desc()).all()

        def serialize_comment(comment):
            return {
                "id": comment.id,
                "content": comment.content,
                "username": comment.user.display_name if comment.user else "알수없음",
                "user_id": comment.user_id,
                "created_at": comment.create_date.strftime("%Y-%m-%d %H:%M"),
                "replies": [
                    serialize_comment(reply) for reply in comment.replies
                ],
            }

        return jsonify(
            user_sarangdal=user_sarangdal,
            photos=[
                {
                    "id": photo.id,
                    "image_url": photo.image_url,
                    "caption": photo.caption,
                    "created_at": photo.create_date.strftime("%Y-%m-%d %H:%M"),
                    "owner": {
                        "id": photo.user.id,
                        "username": photo.user.display_name if photo.user else "알수없음",
                    },
                    "comments_allowed": (
                        photo.user_id == current_user_id
                        or photo.user.allow_album_comments
                    ),
                    "like_count": len(photo.likes),
                    "liked": any(
                        like.user_id == current_user_id for like in photo.likes
                    ),
                    "dislike_count": len(photo.dislikes),
                    "disliked": any(
                        dislike.user_id == current_user_id
                        for dislike in photo.dislikes
                    ),
                    "comments": [
                        serialize_comment(comment)
                        for comment in photo.comments
                        if comment.parent_id is None
                    ],
                }
                for photo in photos
            ]
        )

    @app.post("/api/album/photos")
    @login_required
    def user_album_photo_upload():
        image = request.files.get("image")
        caption = request.form.get("caption", "").strip()
        if not image or not image.filename:
            return jsonify(message="올릴 사진을 선택해 주세요."), 400
        extension = Path(Path(image.filename).name).suffix.lower().lstrip(".")
        if extension not in NOTICE_IMAGE_EXTENSIONS:
            return jsonify(message="JPG, PNG, WEBP, GIF 이미지만 올릴 수 있습니다."), 400
        if not (image.mimetype or "").startswith("image/"):
            return jsonify(message="이미지 파일만 올릴 수 있습니다."), 400
        if not is_safe_upload(image, extension, app.config):
            return jsonify(message="이미지 파일 내용이 올바르지 않습니다."), 400
        if len(caption) > 300:
            return jsonify(message="사진 설명은 300자 이하로 입력해 주세요."), 400

        upload_directory = Path(app.config["UPLOAD_FOLDER"])
        upload_directory.mkdir(parents=True, exist_ok=True)
        saved_name = f"user_album_{uuid4().hex}.{extension}"
        image.save(upload_directory / saved_name)
        photo = UserAlbumPhoto(
            user_id=session["user_id"],
            image_url=url_for("uploaded_media", filename=saved_name),
            caption=caption,
            school_name=(
                request.form.get("school", "").strip()
                or db.session.get(User, session["user_id"]).school_name
            ),
        )
        db.session.add(photo)
        actor = db.session.get(User, session["user_id"])
        notify_school_members(
            photo.school_name,
            actor,
            "new_album_photo",
            "📸 새 추억 앨범",
            f"{actor.display_name}님이 앨범에 새 사진을 올려 추억을 공유했습니다.",
            url_for("main_album", school=photo.school_name),
        )
        db.session.commit()
        return jsonify(status="success", photo_id=photo.id), 201

    def _ai_image_limits():
        try:
            user_limit = max(1, int(os.getenv("AI_IMAGE_MONTHLY_LIMIT", "2")))
        except ValueError:
            user_limit = 2
        try:
            global_limit = max(
                1, int(os.getenv("AI_IMAGE_GLOBAL_MONTHLY_LIMIT", "100"))
            )
        except ValueError:
            global_limit = 100
        return user_limit, global_limit

    @app.get("/api/album/ai-image/status")
    @login_required
    def ai_image_status():
        month_key = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m")
        user_limit, global_limit = _ai_image_limits()
        api_configured = bool(os.getenv("STABILITY_API_KEY", "").strip())
        user_used = AiImageUsage.query.filter_by(
            user_id=session["user_id"], month_key=month_key, status="success"
        ).count()
        global_used = AiImageUsage.query.filter_by(
            month_key=month_key, status="success"
        ).count()
        return jsonify(
            available=api_configured,
            user_limit=user_limit,
            user_remaining=max(user_limit - user_used, 0) if api_configured else 0,
            global_limit=global_limit,
            global_remaining=max(global_limit - global_used, 0) if api_configured else 0,
        )

    @app.post("/api/album/ai-image")
    @login_required
    def ai_image_transform():
        import requests

        api_key = os.getenv("STABILITY_API_KEY", "").strip()
        if not api_key:
            return jsonify(message="AI 이미지 API 키가 설정되지 않았습니다."), 503

        image = request.files.get("image")
        style = request.form.get("style", "anime").strip()
        caption = request.form.get("caption", "").strip()
        allowed_styles = {
            "anime": (
                "anime",
                "Polished anime illustration, preserve the same person's identity, "
                "facial features, pose, clothing, composition and background",
            ),
            "comic": (
                "comic-book",
                "Detailed comic book illustration, preserve the same person's identity, "
                "facial features, pose, clothing and composition",
            ),
            "watercolor": (
                "digital-art",
                "Soft watercolor illustration on textured paper, preserve the same person's "
                "identity, facial features, pose and composition",
            ),
        }
        if style not in allowed_styles:
            return jsonify(message="지원하지 않는 AI 스타일입니다."), 400
        if not image or not image.filename:
            return jsonify(message="변환할 사진을 선택해 주세요."), 400
        extension = Path(image.filename).suffix.lower().lstrip(".")
        if extension not in {"jpg", "jpeg", "png", "webp"}:
            return jsonify(message="AI 변환은 JPG, PNG, WEBP 사진만 지원합니다."), 400
        if not (image.mimetype or "").startswith("image/"):
            return jsonify(message="이미지 파일만 AI 변환할 수 있습니다."), 400
        if not is_safe_upload(image, extension, app.config):
            return jsonify(message="이미지 파일 내용이 올바르지 않습니다."), 400
        if len(caption) > 300:
            return jsonify(message="사진 설명은 300자 이하로 입력해 주세요."), 400

        now = datetime.now(timezone(timedelta(hours=9)))
        month_key = now.strftime("%Y-%m")
        user_limit, global_limit = _ai_image_limits()

        stale_before = datetime.utcnow() - timedelta(minutes=10)
        AiImageUsage.query.filter(
            AiImageUsage.status == "processing",
            AiImageUsage.create_date < stale_before,
        ).delete(synchronize_session=False)
        db.session.commit()

        if AiImageUsage.query.filter_by(
            user_id=session["user_id"], month_key=month_key
        ).count() >= user_limit:
            return jsonify(
                message=f"이번 달 AI 사진 변환 {user_limit}회를 모두 사용했습니다."
            ), 429
        if AiImageUsage.query.filter_by(month_key=month_key).count() >= global_limit:
            return jsonify(message="이번 달 사이트 전체 AI 변환 한도에 도달했습니다."), 429

        usage = AiImageUsage(
            user_id=session["user_id"],
            month_key=month_key,
            status="processing",
            style=style,
        )
        db.session.add(usage)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify(message="AI 변환 요청이 이미 처리 중입니다."), 409

        style_preset, prompt = allowed_styles[style]
        saved_path = None
        try:
            response = requests.post(
                "https://api.stability.ai/v2beta/stable-image/generate/sd3",
                headers={
                    "authorization": f"Bearer {api_key}",
                    "accept": "image/*",
                    "stability-client-id": "friendary-album",
                    "stability-client-user-id": str(session["user_id"]),
                },
                files={
                    "image": (
                        secure_filename(image.filename),
                        image.stream,
                        image.mimetype,
                    )
                },
                data={
                    "prompt": prompt,
                    "mode": "image-to-image",
                    "strength": "0.65",
                    "model": "sd3.5-medium",
                    "style_preset": style_preset,
                    "output_format": "webp",
                },
                timeout=120,
            )
            if response.status_code != 200:
                if response.status_code in {402, 429}:
                    message = "AI 크레딧이 부족하거나 잠시 요청이 많습니다."
                elif response.status_code == 403:
                    message = "안전 정책으로 이 사진을 변환할 수 없습니다."
                else:
                    message = "AI 사진 변환에 실패했습니다. 잠시 후 다시 시도해 주세요."
                raise RuntimeError(message)

            upload_directory = Path(app.config["UPLOAD_FOLDER"])
            upload_directory.mkdir(parents=True, exist_ok=True)
            saved_name = f"user_album_ai_{uuid4().hex}.webp"
            saved_path = upload_directory / saved_name
            saved_path.write_bytes(response.content)

            photo = UserAlbumPhoto(
                user_id=session["user_id"],
                image_url=url_for("uploaded_media", filename=saved_name),
                caption=caption,
                school_name=(
                    request.form.get("school", "").strip()
                    or db.session.get(User, session["user_id"]).school_name
                ),
            )
            usage.status = "success"
            usage.completed_at = datetime.utcnow()
            db.session.add(photo)
            db.session.commit()
            return jsonify(status="success", photo_id=photo.id), 201
        except (requests.RequestException, RuntimeError, OSError) as error:
            db.session.rollback()
            if saved_path:
                saved_path.unlink(missing_ok=True)
            reserved_usage = db.session.get(AiImageUsage, usage.id)
            if reserved_usage:
                db.session.delete(reserved_usage)
                db.session.commit()
            return jsonify(message=str(error)), 502

    @app.delete("/api/album/photos/<int:photo_id>")
    @login_required
    def user_album_photo_delete(photo_id):
        """사진 작성자만 DB 기록과 실제 이미지 파일을 삭제할 수 있습니다."""
        photo = db.get_or_404(UserAlbumPhoto, photo_id)
        if photo.user_id != session["user_id"]:
            return jsonify(message="본인이 올린 사진만 삭제할 수 있습니다."), 403

        image_url = photo.image_url
        db.session.delete(photo)
        db.session.commit()

        # uploads 폴더의 개인 앨범 파일만 지우도록 경로와 접두사를 확인합니다.
        upload_directory = Path(app.config["UPLOAD_FOLDER"]).resolve()
        image_path = (upload_directory / Path(image_url).name).resolve()
        if (
            image_path.parent == upload_directory
            and image_path.name.startswith("user_album_")
        ):
            image_path.unlink(missing_ok=True)

        return jsonify(message="사진이 앨범에서 삭제되었습니다.")

    @app.post("/api/album/photos/<int:photo_id>/like")
    @login_required
    def user_album_photo_like(photo_id):
        photo = db.get_or_404(UserAlbumPhoto, photo_id)
        if photo.user_id != session["user_id"] and not photo.user.is_profile_public:
            return jsonify(message="비공개 사진에는 반응할 수 없습니다."), 403

        user = User.query.filter_by(id=session["user_id"]).with_for_update().one()
        balance = _get_or_grant_user_sarangdal(user, persist=False)

        if balance < 1:
            return (
                jsonify(
                    message="보유한 사랑달이 없습니다. (사랑달은 매달 1개씩 자동 지급됩니다)",
                    user_sarangdal=0,
                ),
                400,
            )

        user.sarangdal_balance = balance - 1
        db.session.add(
            UserAlbumLike(photo_id=photo_id, user_id=user.id)
        )
        db.session.commit()

        like_count = UserAlbumLike.query.filter_by(photo_id=photo_id).count()
        dislike_count = UserAlbumDislike.query.filter_by(photo_id=photo_id).count()
        has_disliked = (
            UserAlbumDislike.query.filter_by(
                photo_id=photo_id, user_id=user.id
            ).first()
            is not None
        )
        return jsonify(
            liked=True,
            disliked=has_disliked,
            like_count=like_count,
            dislike_count=dislike_count,
            user_sarangdal=user.sarangdal_balance,
            message=f"사랑달 1개를 선물했습니다! (보유한 사랑달: {user.sarangdal_balance}개)",
        )

    @app.post("/api/album/photos/<int:photo_id>/dislike")
    @login_required
    def user_album_photo_dislike(photo_id):
        photo = db.get_or_404(UserAlbumPhoto, photo_id)
        if photo.user_id != session["user_id"] and not photo.user.is_profile_public:
            return jsonify(message="비공개 사진에는 반응할 수 없습니다."), 403

        user_id = session["user_id"]
        # Serialize the monthly allowance check for this user.
        User.query.filter_by(id=user_id).with_for_update().one()
        existing = UserAlbumDislike.query.filter_by(
            photo_id=photo_id,
            user_id=user_id,
        ).first()

        if existing:
            db.session.delete(existing)
            disliked = False
            msg = "싫어요 반응을 취소했습니다."
        else:
            now_utc = datetime.utcnow()
            start_of_month = now_utc.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            already_used = UserAlbumDislike.query.filter(
                UserAlbumDislike.user_id == user_id,
                UserAlbumDislike.create_date >= start_of_month,
            ).first()

            if already_used:
                return (
                    jsonify(
                        message="이번 달 '싫어요' 기회를 이미 사용하셨습니다. (월 1회 제공)"
                    ),
                    400,
                )

            db.session.add(
                UserAlbumDislike(
                    photo_id=photo_id,
                    user_id=user_id,
                )
            )
            disliked = True
            msg = "싫어요 반응을 남겼습니다. (이번 달 '싫어요' 1회 사용)"

        db.session.commit()

        has_liked = (
            UserAlbumLike.query.filter_by(
                photo_id=photo_id, user_id=user_id
            ).first()
            is not None
        )
        return jsonify(
            liked=has_liked,
            disliked=disliked,
            like_count=UserAlbumLike.query.filter_by(photo_id=photo_id).count(),
            dislike_count=UserAlbumDislike.query.filter_by(
                photo_id=photo_id
            ).count(),
            message=msg,
        )

    @app.post("/api/album/photos/<int:photo_id>/comments")
    @login_required
    def user_album_photo_comment(photo_id):
        photo = db.get_or_404(UserAlbumPhoto, photo_id)
        if (
            photo.user_id != session["user_id"]
            and (
                not photo.user.is_profile_public
                or not photo.user.allow_album_comments
            )
        ):
            return jsonify(message="사진 주인이 댓글 작성을 허용하지 않았습니다."), 403
        data = request.get_json(silent=True) or {}
        content = str(data.get("content", "")).strip()
        parent_id = data.get("parent_id")
        if not content:
            return jsonify(message="댓글 내용을 입력해 주세요."), 400
        if len(content) > 500:
            return jsonify(message="댓글은 500자 이하로 입력해 주세요."), 400
        parent = None
        if parent_id:
            parent = db.session.get(UserAlbumComment, parent_id)
            if not parent or parent.photo_id != photo_id:
                return jsonify(message="답글을 달 댓글을 찾을 수 없습니다."), 400
        comment = UserAlbumComment(
            photo_id=photo_id,
            user_id=session["user_id"],
            parent_id=parent.id if parent else None,
            content=content,
            school_name=photo.school_name,
        )
        db.session.add(comment)
        actor = db.session.get(User, session["user_id"])
        notification_targets = {photo.user_id}
        if parent:
            notification_targets.add(parent.user_id)
        target_url = url_for(
            "main_album",
            school=photo.school_name,
            photo=photo.id,
        )
        for target_user_id in notification_targets:
            add_notification(
                target_user_id,
                "album_reply" if parent else "album_comment",
                "새 앨범 답글" if parent else "새 앨범 댓글",
                (
                    f"{actor.username}님이 회원님의 댓글에 답글을 남겼습니다."
                    if parent and target_user_id == parent.user_id
                    else f"{actor.username}님이 회원님의 사진에 댓글을 남겼습니다."
                ),
                target_url,
                actor.id,
            )
        db.session.commit()
        return jsonify(
            comment={
                "id": comment.id,
                "content": comment.content,
                "username": actor.display_name,
                "user_id": actor.id,
            }
        ), 201

    @app.get("/api/social/users/<int:user_id>")
    @login_required
    def social_user_profile(user_id):
        user = db.get_or_404(User, user_id)
        if user.id != session["user_id"] and not user.is_profile_public:
            return jsonify(message="이 사용자는 프로필을 비공개로 설정했습니다."), 403
        visible_connections = _visible_connections(
            user.id, session["user_id"]
        )
        return jsonify(
            user={
                "id": user.id,
                "username": user.username,
                "school_name": user.school_name or "학교 정보 없음",
                "age": user.age,
                "gender": user.gender,
                "profile_image_url": user.profile_image_url,
            },
            relationship=_relationship_data(session["user_id"], user.id),
            connection_count=len(visible_connections),
            permissions={
                "allow_album_comments": user.allow_album_comments,
                "allow_messages": user.allow_messages,
            },
        )

    @app.post("/api/social/profile-image")
    @login_required
    def social_profile_image_upload():
        """대표사진은 로그인한 본인의 프로필에만 등록할 수 있습니다."""
        image = request.files.get("image")
        if not image or not image.filename:
            return jsonify(message="대표사진으로 사용할 이미지를 선택해 주세요."), 400
        extension = Path(Path(image.filename).name).suffix.lower().lstrip(".")
        if extension not in NOTICE_IMAGE_EXTENSIONS:
            return jsonify(message="JPG, PNG, WEBP, GIF 이미지만 사용할 수 있습니다."), 400
        if not (image.mimetype or "").startswith("image/"):
            return jsonify(message="이미지 파일만 사용할 수 있습니다."), 400
        if not is_safe_upload(image, extension, app.config):
            return jsonify(message="이미지 파일 내용이 올바르지 않습니다."), 400

        upload_directory = Path(app.config["UPLOAD_FOLDER"])
        upload_directory.mkdir(parents=True, exist_ok=True)
        saved_name = f"profile_{session['user_id']}_{uuid4().hex}.{extension}"
        image.save(upload_directory / saved_name)

        user = db.session.get(User, session["user_id"])
        previous_url = user.profile_image_url
        user.profile_image_url = url_for(
            "uploaded_media", filename=saved_name
        )
        db.session.commit()

        # 교체 전 대표사진 중 이 기능으로 만든 파일만 안전하게 정리합니다.
        if previous_url:
            previous_path = (upload_directory / Path(previous_url).name).resolve()
            if (
                previous_path.parent == upload_directory.resolve()
                and previous_path.name.startswith(f"profile_{user.id}_")
            ):
                previous_path.unlink(missing_ok=True)
        return jsonify(
            message="대표사진이 등록되었습니다.",
            profile_image_url=user.profile_image_url,
        )

    @app.get("/api/social/users/<int:user_id>/connections")
    @login_required
    def social_user_connections(user_id):
        """한 페이지에 30명씩 이 사용자의 1촌 목록을 제공합니다."""
        owner = db.get_or_404(User, user_id)
        if owner.id != session["user_id"] and not owner.is_profile_public:
            return jsonify(message="이 사용자의 인맥은 비공개입니다."), 403
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = 30
        connections = _visible_connections(user_id, session["user_id"])
        total = len(connections)
        pages = max((total + per_page - 1) // per_page, 1)
        if page > pages:
            page = pages
        start = (page - 1) * per_page
        page_connections = connections[start : start + per_page]
        return jsonify(
            connections=[
                {
                    "id": connection.id,
                    "username": connection.username,
                    "school_name": connection.school_name or "학교 정보 없음",
                    "profile_image_url": connection.profile_image_url,
                    "relationship": _relationship_data(
                        session["user_id"], connection.id
                    ),
                }
                for connection in page_connections
            ],
            pagination={
                "page": page,
                "pages": pages,
                "per_page": per_page,
                "total": total,
                "has_prev": page > 1,
                "has_next": page < pages,
            },
        )

    @app.get("/api/social/users")
    @login_required
    def social_user_list():
        """친구 찾기 화면에 전체 가입자와 나와의 관계 상태를 제공합니다."""

        search = request.args.get("q", "").strip()
        school = request.args.get("school", "").strip()
        gender = request.args.get("gender", "").strip()
        age = request.args.get("age", type=int)

        current_user_id = session["user_id"]

        if not search and not school and not gender and age is None:
            return jsonify(
                users=[],
                message="검색 조건을 하나 이상 입력해 주세요."
            )

        related_rows = Friendship.query.filter(
            or_(
                Friendship.requester_id == current_user_id,
                Friendship.receiver_id == current_user_id,
            )
        ).all()

        related_user_ids = {
            row.receiver_id
            if row.requester_id == current_user_id
            else row.requester_id
            for row in related_rows
        }

        query = User.query.filter(
            User.id != current_user_id,
            User.is_profile_public.is_(True),
            User.allow_friend_search.is_(True),
        )

        if related_user_ids:
            query = query.filter(~User.id.in_(related_user_ids))

        if search:
            query = query.filter(User.username.ilike(f"%{search}%"))

        if school:
            query = query.filter(User.school_name.ilike(f"%{school}%"))

        if age is not None:
            query = query.filter(User.age == age)

        if gender in {"male", "female", "other"}:
            query = query.filter(User.gender == gender)

        users = query.order_by(User.username.asc()).limit(100).all()

        return jsonify(
            users=[
                {
                    "id": user.id,
                    "username": user.username,
                    "school_name": user.school_name or "학교 정보 없음",
                    "age": user.age,
                    "gender": user.gender,
                    "relationship": _relationship_data(
                        current_user_id, user.id
                    ),
                }
                for user in users
            ]
        )

    @app.post("/api/social/friends/<int:user_id>/request")
    @login_required
    def friendship_request(user_id):
        target_user = db.get_or_404(User, user_id)
        current_user_id = session["user_id"]
        if current_user_id == user_id:
            return jsonify(message="자기 자신에게는 1촌 신청을 보낼 수 없습니다."), 400
        if not target_user.is_profile_public:
            return jsonify(message="상대방이 프로필을 비공개로 설정했습니다."), 403
        relationship = _friendship_between(current_user_id, user_id)
        if relationship:
            relationship_data = _relationship_data(current_user_id, user_id)
            return jsonify(
                message=relationship_data["label"],
                relationship=relationship_data,
            ), 409
        db.session.add(
            Friendship(requester_id=current_user_id, receiver_id=user_id)
        )
        db.session.commit()
        return jsonify(
            message="1촌 신청을 보냈습니다.",
            relationship=_relationship_data(current_user_id, user_id),
        ), 201

    @app.post("/api/social/friends/<int:friendship_id>/accept")
    @login_required
    def friendship_accept(friendship_id):
        friendship = db.get_or_404(Friendship, friendship_id)
        if friendship.receiver_id != session["user_id"]:
            return jsonify(message="이 1촌 신청을 수락할 권한이 없습니다."), 403
        friendship.status = "accepted"
        friendship.accepted_date = datetime.utcnow()
        db.session.commit()
        return jsonify(message="이제 서로의 추억을 나누는 1촌이 되었습니다 ✨")

    @app.delete("/api/social/friends/<int:friendship_id>")
    @login_required
    def friendship_delete(friendship_id):
        friendship = db.get_or_404(Friendship, friendship_id)
        current_user_id = session["user_id"]
        if current_user_id not in {
            friendship.requester_id,
            friendship.receiver_id,
        }:
            return jsonify(message="이 1촌 관계를 삭제할 권한이 없습니다."), 403
        if friendship.status != "accepted":
            return jsonify(message="수락된 1촌 관계만 삭제할 수 있습니다."), 409

        db.session.delete(friendship)
        db.session.commit()
        return jsonify(message="1촌 관계를 삭제했습니다.")

    @app.get("/api/social/friends")
    @login_required
    def friendship_list():
        current_user_id = session["user_id"]
        rows = Friendship.query.filter(
            or_(
                Friendship.requester_id == current_user_id,
                Friendship.receiver_id == current_user_id,
            )
        ).order_by(Friendship.create_date.desc()).all()
        friends = []
        requests = []
        for friendship in rows:
            other = (
                friendship.receiver
                if friendship.requester_id == current_user_id
                else friendship.requester
            )
            item = {
                "friendship_id": friendship.id,
                "user_id": other.id,
                "username": other.username,
            }
            if not other.is_profile_public:
                continue
            if friendship.status == "accepted":
                friends.append(item)
            elif friendship.receiver_id == current_user_id:
                requests.append(item)
        return jsonify(friends=friends, requests=requests)

    @app.post("/api/social/presence")
    @login_required
    def social_presence():
        """현재 사용자의 접속 신호를 기록하고 접속 중인 승인된 1촌만 반환합니다."""
        current_user_id = session["user_id"]
        now = datetime.utcnow()
        current_user = db.session.get(User, current_user_id)
        if not current_user:
            session.clear()
            return jsonify(error="로그인이 필요합니다."), 401

        current_user.last_active_at = now
        db.session.commit()

        online_since = now - timedelta(seconds=90)
        online_friends = [
            friend
            for friend in _accepted_connections(current_user_id)
            if friend.last_active_at and friend.last_active_at >= online_since
        ]
        return jsonify(
            friends=[
                {
                    "user_id": friend.id,
                    "friendship_id": _friendship_between(
                        current_user_id, friend.id
                    ).id,
                    "username": friend.username,
                    "profile_image_url": friend.profile_image_url,
                }
                for friend in online_friends
            ]
        )

    def _purge_expired_direct_messages():
        """쪽지는 생성 후 최대 30일까지만 보관합니다."""
        expires_before = datetime.utcnow() - timedelta(days=30)
        return DirectMessage.query.filter(
            DirectMessage.create_date < expires_before
        ).delete(synchronize_session=False)

    @app.get("/api/social/messages")
    @login_required
    def direct_message_list():
        if _purge_expired_direct_messages():
            db.session.commit()
        messages = DirectMessage.query.filter_by(
            receiver_id=session["user_id"]
        ).order_by(DirectMessage.create_date.desc()).limit(100).all()
        return jsonify(
            unread_count=sum(not message.is_read for message in messages),
            messages=[
                {
                    "id": message.id,
                    "sender_id": message.sender_id,
                    "sender": message.sender.username,
                    "content": message.content,
                    "is_read": message.is_read,
                    "created_at": message.create_date.strftime("%Y-%m-%d %H:%M"),
                }
                for message in messages
            ],
        )

    @app.delete("/api/social/messages/received/<int:message_id>")
    @login_required
    def direct_message_received_delete(message_id):
        message = DirectMessage.query.filter_by(
            id=message_id,
            receiver_id=session["user_id"],
        ).first()
        if not message:
            return jsonify(message="삭제할 받은 쪽지를 찾을 수 없습니다."), 404
        db.session.delete(message)
        db.session.commit()
        return jsonify(message="받은 쪽지를 삭제했습니다.")

    @app.delete("/api/social/messages/received")
    @login_required
    def direct_message_received_delete_all():
        deleted_count = DirectMessage.query.filter_by(
            receiver_id=session["user_id"]
        ).delete(synchronize_session=False)
        db.session.commit()
        return jsonify(
            message=f"받은 쪽지 {deleted_count}개를 모두 삭제했습니다.",
            deleted_count=deleted_count,
        )

    @app.get("/api/social/messages/sent")
    @login_required
    def direct_message_sent_list():
        if _purge_expired_direct_messages():
            db.session.commit()
        messages = DirectMessage.query.filter_by(
            sender_id=session["user_id"]
        ).order_by(DirectMessage.create_date.desc()).limit(100).all()
        return jsonify(
            messages=[
                {
                    "id": message.id,
                    "receiver_id": message.receiver_id,
                    "receiver": message.receiver.username,
                    "content": message.content,
                    "is_read": message.is_read,
                    "created_at": message.create_date.strftime("%Y-%m-%d %H:%M"),
                }
                for message in messages
            ]
        )

    @app.delete("/api/social/messages/sent/<int:message_id>")
    @login_required
    def direct_message_sent_delete(message_id):
        message = DirectMessage.query.filter_by(
            id=message_id,
            sender_id=session["user_id"],
        ).first()
        if not message:
            return jsonify(message="삭제할 보낸 쪽지를 찾을 수 없습니다."), 404
        db.session.delete(message)
        db.session.commit()
        return jsonify(message="보낸 쪽지를 삭제했습니다.")

    @app.delete("/api/social/messages/sent")
    @login_required
    def direct_message_sent_delete_all():
        deleted_count = DirectMessage.query.filter_by(
            sender_id=session["user_id"]
        ).delete(synchronize_session=False)
        db.session.commit()
        return jsonify(
            message=f"보낸 쪽지 {deleted_count}개를 모두 삭제했습니다.",
            deleted_count=deleted_count,
        )

    @app.post("/api/social/messages")
    @login_required
    def direct_message_send():
        _purge_expired_direct_messages()
        data = request.get_json(silent=True) or {}
        receiver_id = data.get("receiver_id")
        content = str(data.get("content", "")).strip()
        receiver = db.session.get(User, receiver_id) if receiver_id else None
        if not receiver or receiver.id == session["user_id"]:
            return jsonify(message="쪽지를 받을 사용자를 확인해 주세요."), 400
        if not receiver.is_profile_public or not receiver.allow_messages:
            return jsonify(message="상대방이 쪽지 수신을 허용하지 않았습니다."), 403
        if not content:
            return jsonify(message="쪽지 내용을 입력해 주세요."), 400
        if len(content) > 1000:
            return jsonify(message="쪽지는 1000자 이하로 입력해 주세요."), 400
        sender = db.session.get(User, session["user_id"])
        message = DirectMessage(
            sender_id=sender.id,
            receiver_id=receiver.id,
            content=content,
        )
        db.session.add(message)
        db.session.flush()
        add_notification(
            receiver.id,
            "direct_message",
            "새 쪽지",
            f"{sender.username}님이 새 쪽지를 보냈습니다.",
            url_for("main_album", open="messages", message=message.id),
            sender.id,
        )
        db.session.commit()
        return jsonify(message=f"{receiver.username}님께 쪽지를 보냈습니다."), 201

    @app.post("/api/social/messages/read")
    @login_required
    def direct_messages_read():
        _purge_expired_direct_messages()
        DirectMessage.query.filter_by(
            receiver_id=session["user_id"],
            is_read=False,
        ).update({"is_read": True})
        db.session.commit()
        return jsonify(status="success")

    @app.get("/api/social/chat/<int:target_id>")
    @login_required
    def direct_message_conversation(target_id):
        _purge_expired_direct_messages()
        current_id = session["user_id"]
        target = db.get_or_404(User, target_id)
        messages = (
            DirectMessage.query.filter(
                or_(
                    (
                        (DirectMessage.sender_id == current_id)
                        & (DirectMessage.receiver_id == target_id)
                    ),
                    (
                        (DirectMessage.sender_id == target_id)
                        & (DirectMessage.receiver_id == current_id)
                    ),
                )
            )
            .order_by(DirectMessage.create_date.asc())
            .limit(50)
            .all()
        )

        DirectMessage.query.filter_by(
            sender_id=target_id,
            receiver_id=current_id,
            is_read=False,
        ).update({"is_read": True})
        db.session.commit()

        return jsonify(
            target={
                "id": target.id,
                "username": target.username,
                "profile_image_url": target.profile_image_url,
            },
            messages=[
                {
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "receiver_id": msg.receiver_id,
                    "content": msg.content,
                    "created_at": msg.create_date.strftime("%H:%M"),
                }
                for msg in messages
            ],
        )

    def _classroom_participant(room_id, user_id):
        return ClassroomParticipant.query.filter_by(
            room_id=room_id, user_id=user_id
        ).first()

    def _classroom_friend_allowed(first_id, second_id):
        friendship = _friendship_between(first_id, second_id)
        return bool(friendship and friendship.status == "accepted")

    def _classroom_payload(room, current_user_id):
        people = []
        for item in room.participants:
            people.append({
                "user_id": item.user_id,
                "username": item.user.username,
                "slot": item.slot_number,
                "avatar_url": item.user.profile_image_url or url_for(
                    "static",
                    filename="images/avatar_female.png" if item.user.gender == "female" else "images/avatar_male.png",
                ),
                "joined": item.joined_at is not None,
                "is_me": item.user_id == current_user_id,
                "is_owner": item.user_id == room.owner_id,
            })
        return {
            "id": room.id,
            "owner_id": room.owner_id,
            "is_owner": room.owner_id == current_user_id,
            "capacity": 8,
            "participants": people,
        }

    def _get_or_create_owned_classroom(owner_id):
        room = ClassroomRoom.query.filter_by(owner_id=owner_id, is_active=True).first()
        if room:
            return room
        now = datetime.utcnow()
        room = ClassroomRoom(owner_id=owner_id, updated_at=now)
        db.session.add(room)
        db.session.flush()
        db.session.add(ClassroomParticipant(
            room_id=room.id,
            user_id=owner_id,
            slot_number=1,
            joined_at=now,
            last_seen_at=now,
        ))
        db.session.flush()
        return room

    def _invite_to_classroom(room, target):
        if not _classroom_friend_allowed(room.owner_id, target.id):
            return None, "수락된 1촌만 교실에 초대할 수 있습니다."
        existing = _classroom_participant(room.id, target.id)
        if existing:
            return existing, None
        used_slots = {item.slot_number for item in room.participants}
        free_slot = next((slot for slot in range(2, 9) if slot not in used_slots), None)
        if free_slot is None:
            return None, "교실은 방장을 포함해 최대 8명까지 입장할 수 있습니다."
        participant = ClassroomParticipant(
            room_id=room.id,
            user_id=target.id,
            slot_number=free_slot,
        )
        db.session.add(participant)
        return participant, None

    @app.post("/api/social/classroom/start")
    @login_required
    def classroom_start():
        target_id = (request.get_json(silent=True) or {}).get("target_id")
        target = db.session.get(User, target_id) if target_id else None
        current_id = session["user_id"]
        if not target or target.id == current_id:
            return jsonify(message="대화할 1촌을 확인해 주세요."), 400
        room = _get_or_create_owned_classroom(current_id)
        _, error = _invite_to_classroom(room, target)
        if error:
            db.session.rollback()
            return jsonify(message=error), 409
        room.updated_at = datetime.utcnow()
        add_notification(
            target.id, "classroom_invite", "교실 대화 초대",
            f"{db.session.get(User, current_id).username}님이 교실 대화에 초대했습니다.",
            url_for("my_home", room=room.id), current_id,
        )
        db.session.commit()
        return jsonify(room_id=room.id, room_url=url_for("my_home", room=room.id))

    @app.post("/api/social/classroom/<int:room_id>/invite")
    @login_required
    def classroom_room_invite(room_id):
        room = ClassroomRoom.query.filter_by(id=room_id, is_active=True).with_for_update().first_or_404()
        if room.owner_id != session["user_id"]:
            return jsonify(message="방장만 1촌을 초대할 수 있습니다."), 403
        target_id = (request.get_json(silent=True) or {}).get("target_id")
        target = db.session.get(User, target_id) if target_id else None
        if not target or target.id == room.owner_id:
            return jsonify(message="초대할 1촌을 확인해 주세요."), 400
        _, error = _invite_to_classroom(room, target)
        if error:
            db.session.rollback()
            return jsonify(message=error), 409
        room.updated_at = datetime.utcnow()
        add_notification(
            target.id, "classroom_invite", "교실 소환 초대",
            f"{room.owner.username}님이 교실로 초대했습니다.",
            url_for("my_home", room=room.id), room.owner_id,
        )
        db.session.commit()
        return jsonify(message=f"{target.username}님을 교실로 초대했습니다.", room_id=room.id)

    @app.post("/api/social/classroom/<int:room_id>/join")
    @login_required
    def classroom_join(room_id):
        room = ClassroomRoom.query.filter_by(id=room_id, is_active=True).first_or_404()
        participant = _classroom_participant(room.id, session["user_id"])
        if not participant:
            return jsonify(message="이 교실에 초대받지 않았습니다."), 403
        now = datetime.utcnow()
        participant.joined_at = participant.joined_at or now
        participant.last_seen_at = now
        db.session.commit()
        return jsonify(room=_classroom_payload(room, session["user_id"]))

    @app.get("/api/social/classroom/<int:room_id>")
    @login_required
    def classroom_state(room_id):
        room = ClassroomRoom.query.filter_by(id=room_id, is_active=True).first_or_404()
        participant = _classroom_participant(room.id, session["user_id"])
        if not participant or not participant.joined_at:
            return jsonify(message="교실 참가자만 상태를 볼 수 있습니다."), 403
        participant.last_seen_at = datetime.utcnow()
        db.session.commit()
        return jsonify(room=_classroom_payload(room, session["user_id"]))

    @app.get("/api/social/classroom/<int:room_id>/messages")
    @login_required
    def classroom_message_list(room_id):
        participant = _classroom_participant(room_id, session["user_id"])
        if not participant or not participant.joined_at:
            return jsonify(message="교실 참가자만 대화를 볼 수 있습니다."), 403
        after_id = max(request.args.get("after", 0, type=int), 0)
        messages = ClassroomMessage.query.filter(
            ClassroomMessage.room_id == room_id,
            ClassroomMessage.id > after_id,
        ).order_by(ClassroomMessage.id.asc()).limit(100).all()
        return jsonify(messages=[{
            "id": item.id,
            "sender_id": item.sender_id,
            "content": item.content,
            "created_at": item.create_date.strftime("%H:%M"),
        } for item in messages])

    @app.post("/api/social/classroom/<int:room_id>/messages")
    @login_required
    def classroom_message_create(room_id):
        participant = _classroom_participant(room_id, session["user_id"])
        if not participant or not participant.joined_at:
            return jsonify(message="교실 참가자만 대화할 수 있습니다."), 403
        content = str((request.get_json(silent=True) or {}).get("content", "")).strip()
        if not content:
            return jsonify(message="대화 내용을 입력해 주세요."), 400
        if len(content) > 200:
            return jsonify(message="교실 대화는 200자 이하로 입력해 주세요."), 400
        message = ClassroomMessage(room_id=room_id, sender_id=session["user_id"], content=content)
        participant.last_seen_at = datetime.utcnow()
        db.session.add(message)
        db.session.commit()
        return jsonify(message_id=message.id), 201

    @app.post("/api/social/classroom/<int:room_id>/leave")
    @login_required
    def classroom_leave(room_id):
        room = ClassroomRoom.query.filter_by(id=room_id, is_active=True).first_or_404()
        participant = _classroom_participant(room.id, session["user_id"])
        if not participant:
            return jsonify(message="교실 참가자가 아닙니다."), 404
        if room.owner_id == session["user_id"]:
            room.is_active = False
        else:
            db.session.delete(participant)
        db.session.commit()
        return jsonify(message="교실에서 나왔습니다.")

    @app.post("/api/social/classroom/invite")
    @login_required
    def classroom_invite():
        data = request.get_json(silent=True) or {}
        target_id = data.get("target_id")
        target_user = db.session.get(User, target_id) if target_id else None
        if not target_user or target_user.id == session["user_id"]:
            return jsonify(message="소환할 1촌을 확인해 주세요."), 400

        current_user = db.session.get(User, session["user_id"])
        if not _classroom_friend_allowed(current_user.id, target_user.id):
            return jsonify(message="수락된 1촌만 교실에 초대할 수 있습니다."), 403
        room = _get_or_create_owned_classroom(current_user.id)
        _, error = _invite_to_classroom(room, target_user)
        if error:
            db.session.rollback()
            return jsonify(message=error), 409
        room.updated_at = datetime.utcnow()
        target_url = url_for("my_home", room=room.id)
        add_notification(
            target_user.id,
            "classroom_invite",
            "교실 소환 초대",
            f"{current_user.username}님이 교실로 초대했습니다.",
            target_url,
            current_user.id,
        )
        db.session.commit()
        return jsonify(
            message=f"{target_user.username}님을 교실로 초대했습니다.",
            room_id=room.id,
            room_url=target_url,
        )

        # Legacy implementation retained below for migration readability; the
        # secured shared-room return above is the only reachable path.
        target_url = url_for("my_home", chat_user=current_user.id)

        add_notification(
            target_user.id,
            "classroom_invite",
            "교실 소환 초대",
            f"{current_user.username}님이 나만의 교실로 회원님을 소환(초대)했습니다! 🏫",
            target_url,
            current_user.id,
        )
        db.session.commit()
        return jsonify(message=f"{target_user.username}님을 교실로 소환(초대)했습니다!")

    @app.route("/user-album")
    @login_required
    def user_album():
        return render_template("user_album.html")

    def _active_board_school():
        """현재 둘러보는 학교를 세션에 보관해 하위 게시판에도 동일하게 적용합니다."""
        requested_school = request.args.get("school", "").strip()
        if requested_school:
            session["active_board_school"] = requested_school[:120]
        user = db.session.get(User, session["user_id"])
        return (
            session.get("active_board_school")
            or (user.school_name if user else "")
            or ""
        )

    def _same_registered_school(user, school_name):
        """실제 학교 등록 내역이 있는 사용자만 해당 학교에 참여할 수 있습니다."""
        if not user or not school_name:
            return False
        target_school = school_name.strip().casefold()
        registered_schools = UserSchool.query.filter_by(user_id=user.id).all()
        return any(
            membership.school_name
            and membership.school_name.strip().casefold() == target_school
            for membership in registered_schools
        )

    def _can_participate_here():
        user = db.session.get(User, session["user_id"])
        return _same_registered_school(user, _active_board_school())

    def _reject_school_write(destination, **values):
        flash("이 학교에 등록된 사용자만 글·댓글·사랑별 기능을 이용할 수 있습니다.")
        return redirect(url_for(destination, **values))

    def _executive_activity(user_id, start_date, end_date):
        comment_score = (
            BoardComment.query.filter(
                BoardComment.user_id == user_id,
                BoardComment.create_date >= start_date,
                BoardComment.create_date < end_date,
            ).count()
            + RecommendationComment.query.filter(
                RecommendationComment.user_id == user_id,
                RecommendationComment.create_date >= start_date,
                RecommendationComment.create_date < end_date,
            ).count()
            + UserAlbumComment.query.filter(
                UserAlbumComment.user_id == user_id,
                UserAlbumComment.create_date >= start_date,
                UserAlbumComment.create_date < end_date,
            ).count()
        )
        like_score = sum(
            len(post.voters)
            for post in BoardPost.query.filter_by(user_id=user_id).all()
        )
        like_score += RecommendationReaction.query.join(
            RecommendationPost
        ).filter(
            RecommendationPost.user_id == user_id,
            RecommendationReaction.reaction == "like",
        ).count()
        like_score += UserAlbumLike.query.join(UserAlbumPhoto).filter(
            UserAlbumPhoto.user_id == user_id
        ).count()
        return comment_score + like_score, comment_score, like_score

    def _maintain_executives():
        """6개월 미접속 해제 및 매년 1월 학교별 최대 3명 선출."""
        now = datetime.utcnow()
        stale_before = now - timedelta(days=183)
        stale_users = User.query.filter(
            User.is_executive.is_(True),
            or_(User.last_login_at.is_(None), User.last_login_at < stale_before),
        ).all()
        for user in stale_users:
            user.is_executive = False
            user.executive_elected_at = None

        if now.month == 1:
            applications = ExecutiveApplication.query.filter_by(
                election_year=now.year,
                status="pending",
            ).all()
            schools = {application.school_name for application in applications}
            start_date = datetime(now.year - 1, 1, 1)
            end_date = datetime(now.year, 1, 1)
            for school_name in schools:
                school_apps = [
                    item for item in applications if item.school_name == school_name
                ]
                for item in school_apps:
                    (
                        item.activity_score,
                        item.comment_score,
                        item.like_score,
                    ) = _executive_activity(item.user_id, start_date, end_date)
                ranked = sorted(
                    school_apps,
                    key=lambda item: (
                        -item.activity_score,
                        -item.comment_score,
                        item.create_date,
                    ),
                )
                User.query.filter(
                    User.school_name == school_name,
                    User.is_executive.is_(True),
                ).update(
                    {"is_executive": False, "executive_elected_at": None},
                    synchronize_session=False,
                )
                for index, item in enumerate(ranked):
                    item.status = "elected" if index < 3 else "not_elected"
                    if index < 3 and item.user:
                        item.user.is_executive = True
                        item.user.executive_elected_at = now
        db.session.commit()

    def _is_executive(user=None):
        user = user or db.session.get(User, session.get("user_id"))
        return bool(user and user.is_executive)

    @app.before_request
    def update_last_login_activity():
        user_id = session.get("user_id")
        if not user_id:
            return
        user = db.session.get(User, user_id)
        now = datetime.utcnow()
        # 6개월 넘게 접속하지 않은 임원은 복귀한 첫 요청에서 먼저 해제합니다.
        if (
            user
            and user.is_executive
            and (
                user.last_login_at is None
                or user.last_login_at < now - timedelta(days=183)
            )
        ):
            user.is_executive = False
            user.executive_elected_at = None
        if user and (
            user.last_login_at is None
            or user.last_login_at < now - timedelta(hours=12)
        ):
            user.last_login_at = now
            db.session.commit()

    @app.route("/board")
    @login_required
    def board():
        active_school = _active_board_school()
        current_user = db.session.get(User, session["user_id"])

        # 실제로 해당 학교에 등록한 회원만 게시판을 볼 수 있습니다.
        if not _same_registered_school(current_user, active_school):
            flash("이 학교에 등록된 회원만 게시판을 볼 수 있습니다.")
            return redirect(url_for("main_album"))

        _maintain_executives()

        search = request.args.get(
            "kw",
            request.args.get("search", ""),
        ).strip()

        page = request.args.get("page", 1, type=int)

        # 현재 접속한 학교의 게시글만 조회합니다.
        post_query = BoardPost.query.filter(
            BoardPost.school_name == active_school
        )

        if search:
            keyword = f"%{search}%"

            post_query = post_query.filter(
                or_(
                    BoardPost.title.ilike(keyword),
                    BoardPost.content.ilike(keyword),
                    BoardPost.author.ilike(keyword),
                    BoardPost.user.has(
                        User.username.ilike(keyword)
                    ),
                    BoardPost.comments.any(
                        BoardComment.content.ilike(keyword)
                    ),
                )
            )

        pagination = post_query.order_by(
            BoardPost.create_date.desc()
        ).paginate(
            page=page,
            per_page=10,
            error_out=False,
        )

        posts = pagination.items

        # BoardNotice에는 현재 school_name 칼럼이 없으므로
        # 공지는 기존 방식대로 조회합니다.
        notice_query = BoardNotice.query

        # 사랑별 글은 현재 학교의 글만 조회합니다.
        recommendation_query = RecommendationPost.query.filter(
            RecommendationPost.school_name == active_school
        )

        if search:
            keyword = f"%{search}%"

            notice_query = notice_query.filter(
                BoardNotice.content.ilike(keyword)
            )

            recommendation_query = recommendation_query.filter(
                or_(
                    RecommendationPost.title.ilike(keyword),
                    RecommendationPost.content.ilike(keyword),
                    RecommendationPost.place_name.ilike(keyword),
                    RecommendationPost.user.has(
                        User.username.ilike(keyword)
                    ),
                )
            )

        notices = notice_query.order_by(
            BoardNotice.create_date.desc()
        ).all()

        recent_recommendations = recommendation_query.order_by(
            RecommendationPost.create_date.desc()
        ).limit(3).all()

        search_result_count = (
            pagination.total
            + len(notices)
            + len(recent_recommendations)
        )

        search_items = []

        if search:
            search_items.extend(
                {
                    "kind": "일반 게시글",
                    "title": post.title,
                    "description": f"작성자 {post.author}",
                    "url": url_for(
                        "board_view",
                        post_id=post.id,
                    ),
                }
                for post in posts
            )

            search_items.extend(
                {
                    "kind": "공지사항",
                    "title": notice.content,
                    "description": notice.create_date.strftime(
                        "%Y-%m-%d"
                    ),
                    "url": (
                        url_for("notice_board")
                        + f"#notice-{notice.id}"
                    ),
                }
                for notice in notices
            )

            search_items.extend(
                {
                    "kind": "사랑별 글",
                    "title": recommendation.title,
                    "description": (
                        f"{recommendation.place_name} · "
                        f"작성자 "
                        f"{recommendation.user.username}"
                    ),
                    "url": url_for(
                        "recommendation_detail",
                        post_id=recommendation.id,
                    ),
                }
                for recommendation in recent_recommendations
            )

        return render_template(
            "board.html",
            posts=posts,
            notices=notices,
            total_count=pagination.total,
            pagination=pagination,
            search=search,
            can_edit_notice=(
                _is_executive()
                and _can_participate_here()
            ),
            can_participate=_can_participate_here(),
            active_school=active_school,
            recent_recommendations=recent_recommendations,
            executive_application=(
                ExecutiveApplication.query.filter_by(
                    user_id=session["user_id"],
                    school_name=active_school,
                    election_year=(
                        datetime.utcnow().year + 1
                    ),
                ).first()
            ),
            executives=User.query.filter_by(
                school_name=active_school,
                is_executive=True,
            ).limit(3).all(),
            search_result_count=search_result_count,
            search_items=search_items,
        )

    @app.post("/executives/apply")
    @login_required
    def executive_apply():
        if not _can_participate_here():
            return _reject_school_write("board")
        user = db.session.get(User, session["user_id"])
        election_year = datetime.utcnow().year + (
            1 if datetime.utcnow().month > 1 else 0
        )
        existing = ExecutiveApplication.query.filter_by(
            user_id=user.id,
            school_name=user.school_name,
            election_year=election_year,
        ).first()
        if existing:
            flash(f"{election_year}년 임원 선출에 이미 신청했습니다.")
        else:
            db.session.add(
                ExecutiveApplication(
                    user_id=user.id,
                    school_name=user.school_name,
                    election_year=election_year,
                )
            )
            db.session.commit()
            flash(f"{election_year}년 임원 후보 신청이 완료되었습니다.")
        return redirect(url_for("board", school=user.school_name))

    @app.route("/board/all")
    @login_required
    def board_all():
        """메인 요약 영역에서 들어오는 일반게시판 전체 목록 화면입니다."""
        _active_board_school()
        search = request.args.get("kw", "").strip()
        page = request.args.get("page", 1, type=int)
        post_query = BoardPost.query

        if search:
            keyword = f"%{search}%"
            post_query = post_query.filter(
                or_(
                    BoardPost.title.ilike(keyword),
                    BoardPost.content.ilike(keyword),
                    BoardPost.author.ilike(keyword),
                    BoardPost.comments.any(
                        BoardComment.content.ilike(keyword)
                    ),
                )
            )

        pagination = post_query.order_by(
            BoardPost.create_date.desc()
        ).paginate(page=page, per_page=10, error_out=False)
        return render_template(
            "board_all.html",
            posts=pagination.items,
            total_count=pagination.total,
            pagination=pagination,
            search=search,
            can_participate=_can_participate_here(),
        )

    @app.get("/tags/<string:tag>")
    @login_required
    def tag_results(tag):
        """#태그가 들어간 모든 주요 게시글과 댓글을 한 화면에 모읍니다."""
        clean_tag = tag.strip().lstrip("#")[:50]
        if not re.fullmatch(r"[0-9A-Za-z가-힣_]{1,50}", clean_tag):
            return render_template("tag_results.html", tag=clean_tag), 400
        token = f"%#{clean_tag}%"
        plain_token = f"%{clean_tag}%"
        tagged_post_ids = [
            row.post_id
            for row in BoardPostMeta.query.filter(
                BoardPostMeta.tags.ilike(plain_token)
            ).all()
        ]
        posts = BoardPost.query.filter(
            or_(
                BoardPost.title.ilike(token),
                BoardPost.content.ilike(token),
                BoardPost.id.in_(tagged_post_ids),
            )
        ).order_by(BoardPost.create_date.desc()).all()
        board_comments = BoardComment.query.filter(
            BoardComment.content.ilike(token)
        ).order_by(BoardComment.create_date.desc()).all()
        notices = BoardNotice.query.filter(
            BoardNotice.content.ilike(token)
        ).order_by(BoardNotice.create_date.desc()).all()
        album_photos = UserAlbumPhoto.query.filter(
            UserAlbumPhoto.caption.ilike(token)
        ).order_by(UserAlbumPhoto.create_date.desc()).all()
        album_comments = UserAlbumComment.query.filter(
            UserAlbumComment.content.ilike(token)
        ).order_by(UserAlbumComment.create_date.desc()).all()
        graduation_comments = AlbumComment.query.filter(
            AlbumComment.text.ilike(token)
        ).order_by(AlbumComment.create_date.desc()).all()
        recommendation_posts = RecommendationPost.query.filter(
            or_(
                RecommendationPost.title.ilike(token),
                RecommendationPost.content.ilike(token),
                RecommendationPost.tags.ilike(plain_token),
            )
        ).order_by(RecommendationPost.create_date.desc()).all()
        total_count = sum(
            len(items)
            for items in (
                posts,
                board_comments,
                notices,
                album_photos,
                album_comments,
                graduation_comments,
                recommendation_posts,
            )
        )
        return render_template(
            "tag_results.html",
            tag=clean_tag,
            total_count=total_count,
            posts=posts,
            board_comments=board_comments,
            notices=notices,
            album_photos=album_photos,
            album_comments=album_comments,
            graduation_comments=graduation_comments,
            recommendation_posts=recommendation_posts,
        )

    def _safe_http_url(value):
        if not value:
            return ""
        parsed = urlparse(value)
        return value if parsed.scheme in {"http", "https"} and parsed.netloc else None

    def _delete_recommendation_file(file_url):
        if not file_url:
            return
        upload_directory = Path(app.config["UPLOAD_FOLDER"]).resolve()
        file_path = (upload_directory / Path(file_url).name).resolve()
        if (
            file_path.parent == upload_directory
            and file_path.name.startswith("recommendation_")
        ):
            file_path.unlink(missing_ok=True)

    def _recommendation_form_data():
        category = request.form.get("category", "")
        place_name = request.form.get("place_name", "").strip()
        region = request.form.get("region", "").strip()
        address = request.form.get("address", "").strip()
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        price_range = request.form.get("price_range", "").strip()
        external_url = _safe_http_url(
            request.form.get("external_url", "").strip()
        )
        map_url = _safe_http_url(request.form.get("map_url", "").strip())
        tags = request.form.get("tags", "").strip()
        promotion_type = request.form.get("promotion_type", "review")
        if category not in RECOMMENDATION_CATEGORIES:
            return None, "사랑별 종류를 선택해 주세요."
        if not place_name or not title or not content:
            return None, "장소명, 제목, 사랑별 내용을 모두 입력해 주세요."
        if external_url is None or map_url is None:
            return None, "외부 링크와 지도 링크는 http 또는 https 주소만 사용할 수 있습니다."
        if promotion_type not in {"review", "self_promo"}:
            return None, "사랑별 성격을 선택해 주세요."
        if len(title) > 200 or len(content) > 10000:
            return None, "제목 또는 사랑별 내용이 너무 깁니다."
        return {
            "category": category,
            "place_name": place_name[:120],
            "region": region[:120],
            "address": address[:255],
            "title": title[:200],
            "content": content,
            "price_range": price_range[:50],
            "external_url": external_url,
            "map_url": map_url,
            "tags": tags[:500],
            "promotion_type": promotion_type,
        }, None

    def _validate_recommendation_uploads(files):
        validated = []
        for uploaded in files:
            if not uploaded or not uploaded.filename:
                continue
            raw_name = Path(uploaded.filename).name
            extension = Path(raw_name).suffix.lower().lstrip(".")
            if extension in NOTICE_IMAGE_EXTENSIONS:
                media_type = "image"
            elif extension in RECOMMENDATION_VIDEO_EXTENSIONS:
                media_type = "video"
            elif extension in RECOMMENDATION_AUDIO_EXTENSIONS:
                media_type = "audio"
            else:
                return None, "사진, 영상(MP4·WEBM), 오디오(MP3·M4A·WAV·OGG)만 올릴 수 있습니다."
            mimetype = uploaded.mimetype or ""
            if (
                media_type == "image"
                and not mimetype.startswith("image/")
            ) or (
                media_type == "video"
                and not mimetype.startswith("video/")
            ) or (
                media_type == "audio"
                and not mimetype.startswith("audio/")
            ):
                return None, "파일 확장자와 실제 미디어 형식이 일치하지 않습니다."
            if not is_safe_upload(uploaded, extension, app.config):
                return None, "미디어 파일 내용이 올바르지 않습니다."
            original_name = secure_filename(raw_name) or f"media.{extension}"
            validated.append(
                (uploaded, extension, media_type, original_name)
            )
        return validated, None

    @app.get("/api/recommendations/places")
    @login_required
    def recommendation_place_search():
        """카카오 키를 노출하지 않고 서버에서 장소 검색 결과만 전달합니다."""
        query = request.args.get("q", "").strip()
        if len(query) < 2:
            return jsonify({"message": "장소명을 두 글자 이상 입력해 주세요."}), 400
        if len(query) > 100:
            return jsonify({"message": "검색어가 너무 깁니다."}), 400

        rest_api_key = app.config.get("KAKAO_REST_API_KEY", "").strip()
        if not rest_api_key:
            return jsonify(
                {"message": "KAKAO_REST_API_KEY가 설정되지 않았습니다."}
            ), 503

        endpoint = "https://dapi.kakao.com/v2/local/search/keyword.json"
        api_request = Request(
            f"{endpoint}?{urlencode({'query': query, 'size': 10})}",
            headers={"Authorization": f"KakaoAK {rest_api_key}"},
        )
        try:
            with urlopen(api_request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403}:
                message = "카카오 REST API 키를 확인해 주세요."
            elif error.code == 429:
                message = "장소 검색 요청이 많습니다. 잠시 후 다시 시도해 주세요."
            else:
                message = "카카오 장소 검색에 실패했습니다."
            return jsonify({"message": message}), 502
        except (URLError, TimeoutError, json.JSONDecodeError):
            return jsonify(
                {"message": "카카오 장소 검색 서버에 연결할 수 없습니다."}
            ), 502

        places = []
        for item in payload.get("documents", []):
            address = item.get("road_address_name") or item.get("address_name", "")
            region_parts = address.split()
            places.append(
                {
                    "id": item.get("id", ""),
                    "name": item.get("place_name", ""),
                    "category": item.get("category_name", ""),
                    "phone": item.get("phone", ""),
                    "address": address,
                    "region": " ".join(region_parts[:2]),
                    "map_url": item.get("place_url", ""),
                }
            )
        return jsonify({"places": places})

    @app.get("/recommendations")
    @login_required
    def recommendation_list():
        _active_board_school()
        search = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        region = request.args.get("region", "").strip()
        tag = request.args.get("tag", "").strip().lstrip("#")
        order = request.args.get("order", "latest")
        page = request.args.get("page", 1, type=int)
        query = RecommendationPost.query
        if search:
            keyword = f"%{search}%"
            query = query.filter(
                or_(
                    RecommendationPost.title.ilike(keyword),
                    RecommendationPost.content.ilike(keyword),
                    RecommendationPost.place_name.ilike(keyword),
                )
            )
        if category in RECOMMENDATION_CATEGORIES:
            query = query.filter(RecommendationPost.category == category)
        if region:
            query = query.filter(RecommendationPost.region.ilike(f"%{region}%"))
        if tag:
            query = query.filter(RecommendationPost.tags.ilike(f"%{tag}%"))
        if order == "popular":
            like_count = (
                db.session.query(func.count(RecommendationReaction.id))
                .filter(
                    RecommendationReaction.post_id == RecommendationPost.id,
                    RecommendationReaction.reaction == "like",
                )
                .correlate(RecommendationPost)
                .scalar_subquery()
            )
            query = query.order_by(
                like_count.desc(),
                RecommendationPost.create_date.desc(),
            )
        else:
            order = "latest"
            query = query.order_by(RecommendationPost.create_date.desc())
        pagination = query.paginate(page=page, per_page=10, error_out=False)
        cards = []
        for post in pagination.items:
            cards.append(
                {
                    "post": post,
                    "cover": next(
                        (
                            media
                            for media in post.media
                            if media.media_type == "image"
                        ),
                        None,
                    ),
                    "likes": sum(
                        reaction.reaction == "like"
                        for reaction in post.reactions
                    ),
                    "comments": len(post.comments),
                }
            )
        return render_template(
            "recommendation_list.html",
            cards=cards,
            pagination=pagination,
            total_count=pagination.total,
            categories=RECOMMENDATION_CATEGORIES,
            search=search,
            selected_category=category,
            region=region,
            tag=tag,
            order=order,
            can_participate=_can_participate_here(),
        )

    @app.route("/recommendations/write", methods=["GET", "POST"])
    @login_required
    def recommendation_write():
        if not _can_participate_here():
            return _reject_school_write("recommendation_list")
        if request.method == "GET":
            return render_template(
                "recommendation_write.html",
                categories=RECOMMENDATION_CATEGORIES,
                post=None,
            )
        values, error = _recommendation_form_data()
        if error:
            flash(error)
            return redirect(url_for("recommendation_write"))
        uploads, error = _validate_recommendation_uploads(
            request.files.getlist("media")
        )
        if error:
            flash(error)
            return redirect(url_for("recommendation_write"))
        if len(uploads) > 3:
            flash("사진과 영상은 합쳐서 최대 3개까지 올릴 수 있습니다.")
            return redirect(url_for("recommendation_write"))
        post = RecommendationPost(
            user_id=session["user_id"],
            school_name=_active_board_school(),
            **values,
        )
        db.session.add(post)
        db.session.flush()
        upload_directory = Path(app.config["UPLOAD_FOLDER"])
        upload_directory.mkdir(parents=True, exist_ok=True)
        for uploaded, extension, media_type, original_name in uploads:
            saved_name = f"recommendation_{uuid4().hex}.{extension}"
            uploaded.save(upload_directory / saved_name)
            db.session.add(
                RecommendationMedia(
                    post_id=post.id,
                    file_url=url_for(
                        "uploaded_media", filename=saved_name
                    ),
                    media_type=media_type,
                    original_name=original_name,
                )
            )
        creator = db.session.get(User, session["user_id"])
        notify_school_members(
            post.school_name,
            creator,
            "new_recommendation",
            "💗 새 사랑별 장소",
            f"{creator.display_name}님이 '{post.title}' 장소를 추천했습니다.",
            url_for("recommendation_detail", post_id=post.id),
        )
        db.session.commit()
        flash("사랑별 글이 등록되었습니다.")
        return redirect(url_for("recommendation_detail", post_id=post.id))

    @app.route(
        "/recommendations/<int:post_id>/edit",
        methods=["GET", "POST"],
    )
    @login_required
    def recommendation_edit(post_id):
        post = db.get_or_404(RecommendationPost, post_id)
        if post.user_id != session["user_id"]:
            flash("작성자만 사랑별 글을 수정할 수 있습니다.")
            return redirect(url_for("recommendation_detail", post_id=post.id))
        if request.method == "GET":
            return render_template(
                "recommendation_write.html",
                categories=RECOMMENDATION_CATEGORIES,
                post=post,
            )
        values, error = _recommendation_form_data()
        if error:
            flash(error)
            return redirect(url_for("recommendation_edit", post_id=post.id))
        remove_ids = {
            int(value)
            for value in request.form.getlist("remove_media")
            if value.isdigit()
        }
        removable = [
            media for media in post.media if media.id in remove_ids
        ]
        remaining_count = len(post.media) - len(removable)
        uploads, error = _validate_recommendation_uploads(
            request.files.getlist("media")
        )
        if error or remaining_count + len(uploads) > 3:
            flash(error or "사진과 영상은 최대 3개까지 유지할 수 있습니다.")
            return redirect(url_for("recommendation_edit", post_id=post.id))
        for key, value in values.items():
            setattr(post, key, value)
        post.modify_date = datetime.utcnow()
        removed_urls = [media.file_url for media in removable]
        for media in removable:
            db.session.delete(media)
        upload_directory = Path(app.config["UPLOAD_FOLDER"])
        upload_directory.mkdir(parents=True, exist_ok=True)
        for uploaded, extension, media_type, original_name in uploads:
            saved_name = f"recommendation_{uuid4().hex}.{extension}"
            uploaded.save(upload_directory / saved_name)
            db.session.add(
                RecommendationMedia(
                    post_id=post.id,
                    file_url=url_for(
                        "uploaded_media", filename=saved_name
                    ),
                    media_type=media_type,
                    original_name=original_name,
                )
            )
        db.session.commit()
        for file_url in removed_urls:
            _delete_recommendation_file(file_url)
        flash("사랑별 글이 수정되었습니다.")
        return redirect(url_for("recommendation_detail", post_id=post.id))

    @app.get("/recommendations/<int:post_id>")
    @login_required
    def recommendation_detail(post_id):
        post = db.get_or_404(RecommendationPost, post_id)
        current_user = db.session.get(User, session["user_id"])
        can_participate = _same_registered_school(current_user, post.school_name)
        post.views += 1
        db.session.commit()
        current_reaction = RecommendationReaction.query.filter_by(
            post_id=post.id,
            user_id=session["user_id"],
        ).first()
        return render_template(
            "recommendation_detail.html",
            post=post,
            category_label=RECOMMENDATION_CATEGORIES.get(
                post.category, "기타"
            ),
            like_count=sum(
                reaction.reaction == "like"
                for reaction in post.reactions
            ),
            dislike_count=sum(
                reaction.reaction == "dislike"
                for reaction in post.reactions
            ),
            current_reaction=(
                current_reaction.reaction if current_reaction else None
            ),
            can_manage=post.user_id == session["user_id"],
            can_participate=can_participate,
            root_comments=[
                comment
                for comment in post.comments
                if comment.parent_id is None
            ],
        )

    @app.post("/recommendations/<int:post_id>/react/<string:reaction>")
    @login_required
    def recommendation_react(post_id, reaction):
        post = db.get_or_404(RecommendationPost, post_id)
        current_user = db.session.get(User, session["user_id"])
        if not _same_registered_school(current_user, post.school_name):
            return _reject_school_write(
                "recommendation_detail", post_id=post.id
            )
        if reaction not in {"like", "dislike"}:
            return redirect(url_for("recommendation_detail", post_id=post.id))
        existing = RecommendationReaction.query.filter_by(
            post_id=post.id,
            user_id=session["user_id"],
        ).first()
        if existing and existing.reaction == reaction:
            db.session.delete(existing)
        elif existing:
            existing.reaction = reaction
        else:
            db.session.add(
                RecommendationReaction(
                    post_id=post.id,
                    user_id=session["user_id"],
                    reaction=reaction,
                )
            )
        db.session.commit()
        return redirect(url_for("recommendation_detail", post_id=post.id))

    @app.post("/recommendations/<int:post_id>/comments")
    @login_required
    def recommendation_comment_create(post_id):
        post = db.get_or_404(RecommendationPost, post_id)
        current_user = db.session.get(User, session["user_id"])
        if not _same_registered_school(current_user, post.school_name):
            return _reject_school_write(
                "recommendation_detail", post_id=post.id
            )
        content = request.form.get("content", "").strip()
        parent_id = request.form.get("parent_id", type=int)
        parent = (
            db.session.get(RecommendationComment, parent_id)
            if parent_id
            else None
        )
        if not content or len(content) > 1000:
            flash("댓글은 1자 이상 1000자 이하로 입력해 주세요.")
        elif parent and parent.post_id != post.id:
            flash("답글을 달 댓글을 찾을 수 없습니다.")
        else:
            comment = RecommendationComment(
                post_id=post.id,
                user_id=current_user.id,
                parent_id=parent.id if parent else None,
                content=content,
                school_name=post.school_name,
            )
            db.session.add(comment)
            notification_targets = {post.user_id}
            if parent:
                notification_targets.add(parent.user_id)
            target_url = url_for("recommendation_detail", post_id=post.id) + "#comments"
            for target_user_id in notification_targets:
                add_notification(
                    target_user_id,
                    "recommendation_reply" if parent else "recommendation_comment",
                    "새 사랑별 답글" if parent else "새 사랑별 댓글",
                    (
                        f"{current_user.username}님이 회원님의 댓글에 답글을 남겼습니다."
                        if parent and target_user_id == parent.user_id
                        else f"{current_user.username}님이 '{post.title}' 글에 댓글을 남겼습니다."
                    ),
                    target_url,
                    current_user.id,
                )
            db.session.commit()
        return redirect(
            url_for("recommendation_detail", post_id=post.id) + "#comments"
        )

    @app.post("/recommendations/<int:post_id>/delete")
    @login_required
    def recommendation_delete(post_id):
        post = db.get_or_404(RecommendationPost, post_id)
        if post.user_id != session["user_id"]:
            flash("작성자만 사랑별 글을 삭제할 수 있습니다.")
            return redirect(url_for("recommendation_detail", post_id=post.id))
        media_urls = [media.file_url for media in post.media]
        db.session.delete(post)
        db.session.commit()
        for file_url in media_urls:
            _delete_recommendation_file(file_url)
        flash("사랑별 글이 삭제되었습니다.")
        return redirect(url_for("recommendation_list"))

    @app.route("/board/view/<int:post_id>")
    @login_required
    def board_view(post_id):
        post = db.get_or_404(BoardPost, post_id)
        user = db.session.get(User, session["user_id"])

        # 해당 게시글의 학교에 실제 등록된 회원만 열람할 수 있습니다.
        if not _same_registered_school(user, post.school_name):
            flash("이 학교에 등록된 회원만 게시글을 볼 수 있습니다.")
            return redirect(
                url_for(
                    "main_album",
                    school=user.school_name if user else None,
                )
            )

        meta = BoardPostMeta.query.filter_by(
            post_id=post.id
        ).first()

        attachments = BoardAttachment.query.filter_by(
            post_id=post.id
        ).all()

        can_manage = bool(
            user
            and (
                post.user_id == user.id
                or (
                    post.user_id is None
                    and post.author == user.username
                )
            )
        )

        # 비밀글은 작성자만 볼 수 있습니다.
        if meta and meta.is_secret and not can_manage:
            flash("비밀글은 작성자만 볼 수 있습니다.")
            return redirect(
                url_for(
                    "board",
                    school=post.school_name,
                )
            )

        # 권한 검사가 끝난 뒤에만 조회수를 증가시킵니다.
        post.views += 1
        db.session.commit()

        # 이전 글도 같은 학교 글만 조회합니다.
        previous_post = BoardPost.query.filter(
            BoardPost.school_name == post.school_name,
            BoardPost.id < post.id,
        ).order_by(
            BoardPost.id.desc()
        ).first()

        # 다음 글도 같은 학교 글만 조회합니다.
        next_post = BoardPost.query.filter(
            BoardPost.school_name == post.school_name,
            BoardPost.id > post.id,
        ).order_by(
            BoardPost.id.asc()
        ).first()

        return render_template(
            "board_detail.html",
            post=post,
            meta=meta,
            attachments=attachments,
            can_manage=can_manage,
            can_participate=True,
            previous_post=previous_post,
            next_post=next_post,
        )

    @app.route("/board/write", methods=["GET", "POST"])
    @login_required
    def board_write():
        if not session.get("user_id"):
            flash("로그인이 필요합니다.")
            return redirect(url_for("main"))

        if not _can_participate_here():
            return _reject_school_write("board")

        can_write_notice = _is_executive()

        if request.method == "GET":
            return render_template(
                "board_write.html",
                can_write_notice=can_write_notice,
            )

        title = request.form.get("title", "").strip()
        editor_content = request.form.get("content", "").strip()
        content = unescape(re.sub(r"<[^>]+>", " ", editor_content))
        content = re.sub(r"\s+", " ", content).strip()
        tags = request.form.get("tags", "").strip()
        is_secret = request.form.get("is_secret") == "y"
        is_notice = request.form.get("is_notice") == "y"

        if not title or not content:
            flash("제목과 내용을 입력해 주세요.")
            return redirect(url_for("board_write"))
        if len(title) > 200 or len(content) > 20000:
            flash("제목 또는 내용이 너무 깁니다.")
            return redirect(url_for("board_write"))

        user = db.session.get(User, session["user_id"])
        if not user:
            session.clear()
            flash("사용자 정보를 찾을 수 없습니다.")
            return redirect(url_for("main"))

        post = BoardPost(
            title=title,
            content=content,
            author=user.username,
            user_id=user.id,
            school_name=_active_board_school(),
        )
        db.session.add(post)
        db.session.flush()

        db.session.add(
            BoardPostMeta(
                post_id=post.id,
                tags=tags[:500],
                is_secret=is_secret,
            )
        )

        upload_directory = Path(app.config["UPLOAD_FOLDER"])
        upload_directory.mkdir(parents=True, exist_ok=True)

        for field_name in ("file1", "file2"):
            uploaded_file = request.files.get(field_name)
            if not uploaded_file or not uploaded_file.filename:
                continue

            # 한글 파일명도 확장자를 잃지 않도록 원본에서 먼저 확인합니다.
            raw_name = Path(uploaded_file.filename).name
            extension, media_type, media_error = _classify_uploaded_media(
                uploaded_file
            )
            if media_error:
                db.session.rollback()
                flash(
                    "첨부는 JPG·PNG·WEBP·GIF·MP4·WEBM·"
                    "MP3·M4A·WAV·OGG만 사용할 수 있습니다."
                )
                return redirect(url_for("board_write"))

            original_name = secure_filename(raw_name)
            if not original_name:
                original_name = f"media.{extension}"

            saved_name = f"board_{uuid4().hex}.{extension}"
            uploaded_file.save(upload_directory / saved_name)
            db.session.add(
                BoardAttachment(
                    post_id=post.id,
                    file_url=url_for("uploaded_media", filename=saved_name),
                    original_name=original_name,
                    media_type=media_type,
                )
            )

        if is_notice and can_write_notice:
            db.session.add(BoardNotice(content=title))

        notify_school_members(
            post.school_name,
            user,
            "new_post",
            "새 게시글",
            f"{user.display_name}님이 '{post.title}' 글을 올렸습니다.",
            url_for("board_view", post_id=post.id),
        )
        db.session.commit()
        flash("게시글이 등록되었습니다.")
        return redirect(url_for("board"))

    def can_manage_post(post, user):
        return bool(
            user
            and (
                post.user_id == user.id
                or (post.user_id is None and post.author == user.username)
            )
        )

    @app.route("/board/<int:post_id>/edit", methods=["GET", "POST"])
    @login_required
    def board_edit(post_id):
        post = db.get_or_404(BoardPost, post_id)
        user = db.session.get(User, session["user_id"])
        if not can_manage_post(post, user):
            flash("본인이 작성한 게시글만 수정할 수 있습니다.")
            return redirect(url_for("board_view", post_id=post.id))
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            if not title or not content:
                flash("제목과 내용을 입력해 주세요.")
            else:
                post.title = title[:200]
                post.content = content[:20000]
                post.modify_date = datetime.utcnow()
                meta = BoardPostMeta.query.filter_by(post_id=post.id).first()
                if not meta:
                    meta = BoardPostMeta(post_id=post.id)
                    db.session.add(meta)
                meta.tags = request.form.get("tags", "").strip()[:500]
                meta.is_secret = request.form.get("is_secret") == "y"
                db.session.commit()
                flash("게시글이 수정되었습니다.")
                return redirect(url_for("board_view", post_id=post.id))
        meta = BoardPostMeta.query.filter_by(post_id=post.id).first()
        return render_template("board_edit.html", post=post, meta=meta)

    @app.post("/board/<int:post_id>/delete")
    @login_required
    def board_delete(post_id):
        post = db.get_or_404(BoardPost, post_id)
        user = db.session.get(User, session["user_id"])
        if not can_manage_post(post, user):
            flash("본인이 작성한 게시글만 삭제할 수 있습니다.")
            return redirect(url_for("board_view", post_id=post.id))
        BoardAttachment.query.filter_by(post_id=post.id).delete()
        BoardPostMeta.query.filter_by(post_id=post.id).delete()
        db.session.delete(post)
        db.session.commit()
        flash("게시글이 삭제되었습니다.")
        return redirect(url_for("board"))

    @app.post("/board/<int:post_id>/vote")
    @login_required
    def board_vote(post_id):
        post = db.get_or_404(BoardPost, post_id)
        user = db.session.get(User, session["user_id"])
        if not _same_registered_school(user, post.school_name):
            return _reject_school_write("board_view", post_id=post.id)
        if user in post.voters:
            post.voters.remove(user)
        else:
            post.voters.append(user)
            add_notification(
                post.user_id,
                "post_like",
                "게시글 사랑별",
                f"{user.username}님이 '{post.title}' 글에 사랑별을 보냈습니다.",
                url_for("board_view", post_id=post.id),
                user.id,
            )
        db.session.commit()
        return redirect(url_for("board_view", post_id=post.id))

    @app.post("/board/<int:post_id>/comments")
    @login_required
    def comment_create(post_id):
        post = db.get_or_404(BoardPost, post_id)
        user = db.session.get(User, session["user_id"])
        if not _same_registered_school(user, post.school_name):
            return _reject_school_write("board_view", post_id=post.id)
        content = request.form.get("content", "").strip()
        if not content:
            flash("댓글 내용을 입력해 주세요.")
        else:
            comment = BoardComment(
                post_id=post.id,
                user_id=session["user_id"],
                content=content[:2000],
                school_name=post.school_name,
            )
            db.session.add(comment)
            db.session.flush()
            add_notification(
                post.user_id,
                "post_comment",
                "새 댓글",
                f"{user.username}님이 '{post.title}' 글에 댓글을 남겼습니다.",
                url_for("board_view", post_id=post.id)
                + f"#comment-{comment.id}",
                user.id,
            )
            db.session.commit()
            return redirect(
                url_for("board_view", post_id=post.id) + f"#comment-{comment.id}"
            )
        return redirect(url_for("board_view", post_id=post.id))

    @app.post("/board/comments/<int:comment_id>/delete")
    @login_required
    def comment_delete(comment_id):
        comment = db.get_or_404(BoardComment, comment_id)
        post_id = comment.post_id
        if comment.user_id != session["user_id"]:
            flash("본인의 댓글만 삭제할 수 있습니다.")
        else:
            db.session.delete(comment)
            db.session.commit()
        return redirect(url_for("board_view", post_id=post_id))

    @app.route("/board/comments/<int:comment_id>/edit", methods=["GET", "POST"])
    @login_required
    def comment_edit(comment_id):
        comment = db.get_or_404(BoardComment, comment_id)
        if comment.user_id != session["user_id"]:
            flash("본인의 댓글만 수정할 수 있습니다.")
            return redirect(url_for("board_view", post_id=comment.post_id))
        if request.method == "POST":
            content = request.form.get("content", "").strip()
            if content:
                comment.content = content[:2000]
                comment.modify_date = datetime.utcnow()
                db.session.commit()
                return redirect(
                    url_for("board_view", post_id=comment.post_id)
                    + f"#comment-{comment.id}"
                )
            flash("댓글 내용을 입력해 주세요.")
        return render_template("comment_edit.html", comment=comment)

    @app.post("/board/comments/<int:comment_id>/vote")
    @login_required
    def comment_vote(comment_id):
        comment = db.get_or_404(BoardComment, comment_id)
        user = db.session.get(User, session["user_id"])
        post = db.session.get(BoardPost, comment.post_id)
        if not post or not _same_registered_school(user, post.school_name):
            return _reject_school_write(
                "board_view", post_id=comment.post_id
            )
        if user in comment.voters:
            comment.voters.remove(user)
        else:
            comment.voters.append(user)
            add_notification(
                comment.user_id,
                "comment_like",
                "댓글 사랑별",
                f"{user.username}님이 회원님의 댓글에 사랑별을 보냈습니다.",
                url_for("board_view", post_id=comment.post_id)
                + f"#comment-{comment.id}",
                user.id,
            )
        db.session.commit()
        return redirect(
            url_for("board_view", post_id=comment.post_id)
            + f"#comment-{comment.id}"
        )

    @app.get("/api/notifications")
    @login_required
    def notifications_list():
        user_id = session["user_id"]
        user = db.session.get(User, user_id)
        registered_schools = {
            row.school_name
            for row in UserSchool.query.filter_by(user_id=user_id).all()
            if row.school_name
        }
        if user and user.school_name:
            registered_schools.add(user.school_name)

        # Reconcile recent DB activity so notifications created before the
        # notification worker was deployed are also visible. Exact post URLs
        # and message timestamps prevent repeated polling from duplicating rows.
        added_from_database = False
        if registered_schools:
            recent_posts = (
                BoardPost.query.filter(
                    BoardPost.school_name.in_(registered_schools),
                    BoardPost.user_id != user_id,
                )
                .order_by(BoardPost.create_date.desc(), BoardPost.id.desc())
                .limit(20)
                .all()
            )
            for post in recent_posts:
                target_url = url_for("board_view", post_id=post.id)
                exists = Notification.query.filter_by(
                    user_id=user_id,
                    kind="new_post",
                    target_url=target_url,
                ).first()
                if exists:
                    continue
                add_notification(
                    user_id,
                    "new_post",
                    "새 학교 게시글",
                    f"{post.author}님이 '{post.title}' 글을 올렸습니다.",
                    target_url,
                    post.user_id,
                )
                added_from_database = True

        unread_messages = (
            DirectMessage.query.filter_by(receiver_id=user_id, is_read=False)
            .order_by(DirectMessage.create_date.desc(), DirectMessage.id.desc())
            .limit(20)
            .all()
        )
        for message in unread_messages:
            exists = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.kind == "direct_message",
                Notification.actor_id == message.sender_id,
                Notification.create_date >= message.create_date,
            ).first()
            if exists:
                continue
            sender_name = message.sender.display_name if message.sender else "1촌 친구"
            add_notification(
                user_id,
                "direct_message",
                "새 쪽지",
                f"{sender_name}님이 새 쪽지를 보냈습니다.",
                url_for("main_album", open="messages", message=message.id),
                message.sender_id,
            )
            added_from_database = True

        if added_from_database:
            db.session.commit()

        notifications = (
            Notification.query.filter_by(user_id=user_id)
            .order_by(Notification.create_date.desc(), Notification.id.desc())
            .limit(100)
            .all()
        )
        unread_count = Notification.query.filter_by(
            user_id=user_id,
            is_read=False,
        ).count()
        response = jsonify(
            unread_count=unread_count,
            notifications=[
                {
                    "id": item.id,
                    "kind": item.kind,
                    "title": item.title,
                    "message": item.message,
                    "target_url": item.target_url,
                    "is_read": item.is_read,
                    "created_at": item.create_date.isoformat(timespec="minutes"),
                }
                for item in notifications
            ],
        )
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        return response

    @app.post("/api/notifications/<int:notification_id>/read")
    @login_required
    def notification_read(notification_id):
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=session["user_id"],
        ).first_or_404()
        notification.is_read = True
        db.session.commit()
        return jsonify(
            ok=True,
            target_url=notification.target_url,
        )

    @app.post("/api/notifications/read-all")
    @login_required
    def notifications_read_all():
        Notification.query.filter_by(
            user_id=session["user_id"],
            is_read=False,
        ).update({"is_read": True}, synchronize_session=False)
        db.session.commit()
        return jsonify(ok=True, unread_count=0)

    @app.route("/notices")
    @login_required
    def notice_board():
        """현재 등록 학교의 공지만 보여 줍니다."""
        active_school = _active_board_school()
        current_user = db.session.get(
            User,
            session["user_id"],
        )

        if not _same_registered_school(
            current_user,
            active_school,
        ):
            flash("이 학교에 등록된 회원만 공지사항을 볼 수 있습니다.")
            return redirect(url_for("main_album"))

        notices = BoardNotice.query.filter(
            BoardNotice.school_name == active_school
        ).order_by(
            BoardNotice.create_date.desc()
        ).all()

        return render_template(
            "notice_board.html",
            notices=notices,
            can_edit_notice=(
                _is_executive()
                and _can_participate_here()
            ),
            can_participate=True,
            active_school=active_school,
        )

    @app.route("/notice/edit", methods=["GET", "POST"])
    @login_required
    def notice_edit():
        if not _can_participate_here():
            return _reject_school_write("notice_board")
        can_edit_notice = _is_executive()
        notices = BoardNotice.query.order_by(BoardNotice.create_date.desc()).all()
        notice_id = request.args.get("notice_id", type=int)
        selected_notice = (
            db.session.get(BoardNotice, notice_id) if notice_id else None
        )

        if request.method == "GET":
            return render_template(
                "notice_edit.html",
                can_edit_notice=can_edit_notice,
                notice=selected_notice,
                notices=notices,
            )

        if not can_edit_notice:
            return (
                render_template(
                    "notice_edit.html",
                    can_edit_notice=False,
                    notice=None,
                    notices=notices,
                ),
                403,
            )

        action = request.form.get("action", "save")
        notice_id = request.form.get("notice_id", type=int)
        notice = db.session.get(BoardNotice, notice_id) if notice_id else None

        # 삭제는 POST 요청으로만 처리해 주소 클릭만으로 지워지지 않게 합니다.
        if action == "delete":
            if not notice:
                flash("삭제할 공지사항을 찾을 수 없습니다.")
                return redirect(url_for("notice_edit"))
            _delete_notice_image(app, notice.image_url)
            db.session.delete(notice)
            db.session.commit()
            flash("공지사항이 삭제되었습니다.")
            return redirect(url_for("notice_board"))

        notice_content = request.form.get("notice_content", "").strip()
        if not notice_content:
            flash("공지 내용을 입력해 주세요.")
            return redirect(
                url_for("notice_edit", notice_id=notice_id)
                if notice_id
                else url_for("notice_edit")
            )
        if len(notice_content) > 300:
            flash("공지 내용은 300자 이하로 입력해 주세요.")
            return redirect(
                url_for("notice_edit", notice_id=notice_id)
                if notice_id
                else url_for("notice_edit")
            )

        image = request.files.get("notice_image")
        remove_image = request.form.get("remove_image") == "1"
        if image and image.filename:
            (
                image_url,
                media_type,
                original_name,
                error_message,
            ) = _save_notice_media(app, image)
            if error_message:
                flash(error_message)
                return redirect(
                    url_for("notice_edit", notice_id=notice_id)
                    if notice_id
                    else url_for("notice_edit")
                )
            if notice:
                _delete_notice_image(app, notice.image_url)
        else:
            image_url = notice.image_url if notice else None
            media_type = notice.media_type if notice else "image"
            original_name = notice.original_name if notice else None

        if remove_image and not (image and image.filename):
            if notice:
                _delete_notice_image(app, notice.image_url)
            image_url = None
            media_type = "image"
            original_name = None

        if notice:
            notice.content = notice_content
            notice.image_url = image_url
            notice.media_type = media_type
            notice.original_name = original_name
            notice.modify_date = datetime.utcnow()
        else:
            db.session.add(
                BoardNotice(
                    school_name=_active_board_school(),
                    content=notice_content,
                    image_url=image_url,
                    media_type=media_type,
                    original_name=original_name,
                )
            )

        if not notice:
            creator = db.session.get(User, session["user_id"])
            notify_school_members(
                _active_board_school(),
                creator,
                "new_notice",
                "📢 새 공지사항",
                f"{creator.display_name}님이 새 공지사항을 등록했습니다.",
                url_for("notice_board"),
            )
        db.session.commit()
        flash("공지사항이 수정되었습니다." if notice else "공지사항이 등록되었습니다.")
        return redirect(url_for("notice_board"))



    @app.route("/forgot-password")
    def forgot_password():
        return render_template("forgot.html")

    @app.route("/find-id")
    def find_id():
        return render_template("find_id.html")

    @app.route("/phone-auth")
    def phone_auth():
        return render_template("phone_auth.html")




    # ==========================================
    # 아이디 찾기 / 비밀번호 찾기 / 휴대폰 본인인증 API
    # ==========================================

    @app.post("/api/auth/find-id/request")
    @rate_limit(limit=5, window=300, scope="find-id")
    def api_find_id_request():
        session.pop("verification_find_id", None)
        if not app.config.get("AUTH_TEST_MODE") and not app.config.get("SMTP_HOST"):
            return jsonify({"success": False, "message": "본인인증 서비스가 아직 연결되지 않았습니다."}), 503
        data = request.get_json() or {}
        query_val = data.get("query", "").strip()

        if not query_val:
            return jsonify({"success": False, "message": "전화번호 또는 이메일을 입력해 주세요."}), 400

        clean_query = query_val.replace("-", "").replace(" ", "").lower()
        target_user = User.query.filter(
            or_(func.lower(User.email) == clean_query, func.lower(User.username) == clean_query)
        ).first()

        if not target_user:
            # Do not disclose whether an account exists.
            return jsonify({
                "success": True,
                "message": "입력한 정보와 일치하는 계정이 있으면 인증번호가 발송됩니다.",
            })

        code = "123456" if app.config.get("AUTH_TEST_MODE") else f"{secrets.randbelow(1000000):06d}"
        if not app.config.get("AUTH_TEST_MODE"):
            try:
                send_email_code(app.config, target_user.email, "아이디 찾기", code)
            except Exception:
                app.logger.exception("Failed to deliver find-id code")
                return jsonify({"success": False, "message": "인증메일 발송에 실패했습니다."}), 502
        create_verification_challenge("find_id", code, target_user)

        email_str = target_user.email
        if "@" in email_str:
            parts = email_str.split("@")
            masked_name = parts[0][:3] + "***" if len(parts[0]) > 3 else parts[0][:1] + "**"
            masked_id = f"{masked_name}@{parts[1]}"
        else:
            masked_id = email_str[:3] + "***" if len(email_str) > 3 else email_str[:1] + "**"

        response = {
            "success": True,
            "message": "입력한 정보와 일치하는 계정이 있으면 인증번호가 발송됩니다.",
        }
        if app.config.get("AUTH_TEST_MODE"):
            response.update(message="인증번호가 발송되었습니다. (테스트 인증번호: 123456)", test_code="123456")
        return jsonify(response)

    @app.post("/api/auth/find-id/verify")
    @rate_limit(limit=10, window=300, scope="find-id-verify")
    def api_find_id_verify():
        if not app.config.get("AUTH_TEST_MODE") and not app.config.get("SMTP_HOST"):
            return jsonify({"success": False, "message": "본인인증 서비스가 비활성화되어 있습니다."}), 503
        data = request.get_json() or {}
        code = data.get("code", "").strip()
        challenge = verify_challenge("find_id", code)
        if challenge and challenge.user:
            real_id = challenge.user.email
            parts = real_id.split("@", 1)
            masked_name = parts[0][:3] + "***" if len(parts[0]) > 3 else parts[0][:1] + "**"
            masked_id = f"{masked_name}@{parts[1]}" if len(parts) == 2 else masked_name

            return jsonify({
                "success": True,
                "masked_id": masked_id or real_id,
                "real_email": real_id,
                "message": f"인증 완료! 회원님의 아이디는 [{masked_id or real_id}] 입니다."
            })

        return jsonify({"success": False, "message": "인증번호가 올바르지 않거나 만료되었습니다."}), 400

    @app.post("/api/auth/forgot-password/check")
    @rate_limit(limit=5, window=300, scope="password-reset")
    def api_forgot_password_check():
        session.pop("verification_password_reset", None)
        if not app.config.get("AUTH_TEST_MODE") and not app.config.get("SMTP_HOST"):
            return jsonify({"success": False, "message": "비밀번호 재설정 인증 서비스가 아직 연결되지 않았습니다."}), 503
        data = request.get_json() or {}
        login_id = data.get("login_id", "").strip()

        if not login_id:
            return jsonify({"success": False, "message": "아이디를 입력해 주세요."}), 400

        user = User.query.filter(
            (User.email == login_id) | (User.username == login_id)
        ).first()

        if not user:
            # Match the success response shape and timing closely enough to prevent enumeration.
            secrets.token_bytes(32)
            return jsonify({
                "success": True,
                "message": "입력한 정보와 일치하는 계정이 있으면 인증번호가 발송됩니다.",
            })

        code = "123456" if app.config.get("AUTH_TEST_MODE") else f"{secrets.randbelow(1000000):06d}"
        if not app.config.get("AUTH_TEST_MODE"):
            try:
                send_email_code(app.config, user.email, "비밀번호 재설정", code)
            except Exception:
                app.logger.exception("Failed to deliver password reset code")
                return jsonify({"success": False, "message": "인증메일 발송에 실패했습니다."}), 502
        create_verification_challenge("password_reset", code, user)

        response = {
            "success": True,
            "message": "입력한 정보와 일치하는 계정이 있으면 인증번호가 발송됩니다.",
        }
        if app.config.get("AUTH_TEST_MODE"):
            response["message"] = f"{user.username}님의 계정을 찾았습니다. 테스트 인증번호 123456을 입력해 주세요."
            response["test_code"] = "123456"
        return jsonify(response)

    @app.post("/api/auth/forgot-password/reset")
    @rate_limit(limit=10, window=300, scope="password-reset-verify")
    def api_forgot_password_reset():
        if not app.config.get("AUTH_TEST_MODE") and not app.config.get("SMTP_HOST"):
            return jsonify({"success": False, "message": "비밀번호 재설정 서비스가 비활성화되어 있습니다."}), 503
        data = request.get_json() or {}
        code = data.get("code", "").strip()
        new_password = data.get("new_password", "").strip()

        if not new_password or len(new_password) < 8:
            return jsonify({"success": False, "message": "새 비밀번호는 8자 이상 입력해 주세요."}), 400

        challenge = verify_challenge("password_reset", code)
        if not challenge:
            return jsonify({"success": False, "message": "인증번호가 일치하지 않습니다."}), 400

        user = challenge.user
        if not user:
            return jsonify({"success": False, "message": "사용자를 찾을 수 없습니다."}), 404

        user.password = generate_password_hash(new_password)
        user.session_version += 1
        db.session.commit()
        audit_event("password_reset", user_id=user.id)

        return jsonify({
            "success": True,
            "message": "🎉 비밀번호가 성공적으로 변경되었습니다! 새 비밀번호로 로그인해 주세요."
        })

    @app.post("/api/auth/phone-auth/send")
    @rate_limit(limit=5, window=300, scope="phone-auth")
    def api_phone_auth_send():
        session.pop("verification_phone", None)
        if not app.config.get("AUTH_TEST_MODE") and not app.config.get("SMS_API_URL"):
            return jsonify({"success": False, "message": "휴대폰 인증 서비스가 아직 연결되지 않았습니다."}), 503
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        birth = data.get("birth", "").strip()

        if not phone or len(phone.replace("-", "")) < 10:
            return jsonify({"success": False, "message": "올바른 전화번호를 입력해 주세요."}), 400

        code = "123456" if app.config.get("AUTH_TEST_MODE") else f"{secrets.randbelow(1000000):06d}"
        if not app.config.get("AUTH_TEST_MODE"):
            try:
                send_sms_code(app.config, phone, code)
            except Exception:
                app.logger.exception("Failed to deliver phone verification code")
                return jsonify({"success": False, "message": "인증문자 발송에 실패했습니다."}), 502
        create_verification_challenge("phone", code)

        response = {
            "success": True,
            "message": f"[{phone}] 번호로 인증번호가 발송되었습니다.",
        }
        if app.config.get("AUTH_TEST_MODE"):
            response.update(message=f"[{phone}] 테스트 인증번호는 123456입니다.", test_code="123456")
        return jsonify(response)

    @app.post("/api/auth/phone-auth/verify")
    @rate_limit(limit=10, window=300, scope="phone-auth-verify")
    def api_phone_auth_verify():
        if not app.config.get("AUTH_TEST_MODE") and not app.config.get("SMS_API_URL"):
            return jsonify({"success": False, "message": "휴대폰 인증 서비스가 비활성화되어 있습니다."}), 503
        data = request.get_json() or {}
        code = data.get("code", "").strip()
        if not verify_challenge("phone", code):
            return jsonify({"success": False, "message": "인증번호가 일치하지 않습니다."}), 400

        session["phone_verified"] = True
        session["phone_verified_at"] = datetime.now(timezone.utc).timestamp()
        return jsonify({
            "success": True,
            "message": "본인인증이 완료되었습니다."
        })


    @app.route("/login/kakao")
    def kakao_login():
        if not app.config.get("KAKAO_CLIENT_ID"):
            flash("카카오 OAuth 환경변수가 설정되지 않았습니다.")
            return redirect(url_for("main"))

        callback_url = url_for("kakao_callback", _external=True)
        return oauth.kakao.authorize_redirect(callback_url)

    @app.route("/login/kakao/callback")
    def kakao_callback():
        if not app.config.get("KAKAO_CLIENT_ID"):
            flash("카카오 OAuth 환경변수가 설정되지 않았습니다.")
            return redirect(url_for("main"))

        try:
            token = oauth.kakao.authorize_access_token()
            profile_result = oauth.kakao.get("v2/user/me", token=token)
            profile_result.raise_for_status()
            profile = profile_result.json()
        except Exception:
            flash("카카오 로그인이 취소되었거나 인증에 실패했습니다.")
            return redirect(url_for("main"))

        subject = str(profile.get("id", "")).strip()
        kakao_account = profile.get("kakao_account") or {}
        profile_info = kakao_account.get("profile") or {}
        email = str(kakao_account.get("email", "")).strip().lower()
        email_verified = bool(
            kakao_account.get("is_email_valid")
            and kakao_account.get("is_email_verified")
        )
        if not email_verified:
            # An unverified provider address must never be used to attach an existing account.
            email = ""

        if not subject:
            flash("카카오 사용자 정보를 확인할 수 없습니다.")
            return redirect(url_for("main"))

        oauth_account = OAuthAccount.query.filter_by(
            provider="kakao",
            subject=subject,
        ).first()

        if oauth_account:
            user = db.session.get(User, oauth_account.user_id)
        else:
            user = User.query.filter_by(email=email).first() if email_verified and email else None

            if not user:
                base_username = (
                    str(profile_info.get("nickname", "")).strip()
                    or f"kakao_user_{subject[-8:]}"
                )
                username = base_username[:50]
                suffix = 1

                while User.query.filter_by(username=username).first():
                    suffix_text = f"_{suffix}"
                    username = (
                        f"{base_username[: 50 - len(suffix_text)]}{suffix_text}"
                    )
                    suffix += 1

                if not email:
                    email = f"kakao_{subject}@oauth.friendary.local"

                user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(
                        secrets.token_urlsafe(32)
                    ),
                )
                db.session.add(user)
                db.session.flush()

            db.session.add(
                OAuthAccount(
                    provider="kakao",
                    subject=subject,
                    user_id=user.id,
                )
            )
            db.session.commit()

        if not user:
            flash("연결된 사용자 정보를 찾을 수 없습니다.")
            return redirect(url_for("main"))

        establish_login_session(user)

        return login_destination(user)

    @app.route("/login/naver")
    def naver_login():
        if not app.config.get("NAVER_CLIENT_ID") or not app.config.get(
            "NAVER_CLIENT_SECRET"
        ):
            flash("네이버 OAuth 환경변수가 설정되지 않았습니다.")
            return redirect(url_for("main"))

        callback_url = url_for("naver_callback", _external=True)
        return oauth.naver.authorize_redirect(callback_url)

    @app.route("/login/naver/callback")
    def naver_callback():
        if not app.config.get("NAVER_CLIENT_ID") or not app.config.get(
            "NAVER_CLIENT_SECRET"
        ):
            flash("네이버 OAuth 환경변수가 설정되지 않았습니다.")
            return redirect(url_for("main"))

        try:
            token = oauth.naver.authorize_access_token()
            profile_result = oauth.naver.get("v1/nid/me", token=token)
            profile_result.raise_for_status()
            profile = profile_result.json().get("response", {})
        except Exception:
            flash("네이버 로그인이 취소되었거나 인증에 실패했습니다.")
            return redirect(url_for("main"))

        subject = str(profile.get("id", "")).strip()
        email = str(profile.get("email", "")).strip().lower()

        if not subject or not email:
            flash("네이버 계정의 이메일 정보 제공에 동의해 주세요.")
            return redirect(url_for("main"))

        oauth_account = OAuthAccount.query.filter_by(
            provider="naver",
            subject=subject,
        ).first()

        if oauth_account:
            user = db.session.get(User, oauth_account.user_id)
        else:
            # Naver does not return a portable email_verified claim. Never silently
            # attach an existing local account based on this address alone.
            user = User.query.filter_by(email=email).first()
            if user:
                flash("같은 이메일 계정이 있습니다. 먼저 기존 방식으로 로그인해 계정을 연결해 주세요.")
                return redirect(url_for("main"))

            base_username = (
                str(profile.get("name", "")).strip()
                or str(profile.get("nickname", "")).strip()
                or email.split("@", 1)[0]
                or "naver_user"
            )
            username = base_username[:50]

            user = User(
                username=username,
                email=email,
                password=generate_password_hash(
                    secrets.token_urlsafe(32)
                ),
            )
            db.session.add(user)
            db.session.flush()

            db.session.add(
                OAuthAccount(
                    provider="naver",
                    subject=subject,
                    user_id=user.id,
                )
            )
            db.session.commit()

        if not user:
            flash("연결된 사용자 정보를 찾을 수 없습니다.")
            return redirect(url_for("main"))

        establish_login_session(user)

        return login_destination(user)

    @app.route("/login/google")
    def google_login():
        if not app.config.get("GOOGLE_CLIENT_ID") or not app.config.get(
            "GOOGLE_CLIENT_SECRET"
        ):
            flash("Google OAuth 환경변수가 설정되지 않았습니다.")
            return redirect(url_for("main"))

        callback_url = url_for("google_callback", _external=True)
        return oauth.google.authorize_redirect(callback_url)

    @app.route("/login/google/callback")
    def google_callback():
        if not app.config.get("GOOGLE_CLIENT_ID") or not app.config.get(
            "GOOGLE_CLIENT_SECRET"
        ):
            flash("Google OAuth 환경변수가 설정되지 않았습니다.")
            return redirect(url_for("main"))

        try:
            token = oauth.google.authorize_access_token()
        except OAuthError:
            flash("Google 로그인이 취소되었거나 인증에 실패했습니다.")
            return redirect(url_for("main"))

        userinfo = token.get("userinfo") or {}

        subject = str(userinfo.get("sub", "")).strip()
        email = str(userinfo.get("email", "")).strip().lower()
        email_verified = userinfo.get("email_verified", False)
        google_name = str(userinfo.get("name", "")).strip()

        if not subject or not email or not email_verified:
            flash("인증된 Google 이메일 정보를 확인할 수 없습니다.")
            return redirect(url_for("main"))

        # 이미 이 구글 계정으로 가입한 사용자인지 확인합니다.
        oauth_account = OAuthAccount.query.filter_by(
            provider="google",
            subject=subject,
        ).first()

        if oauth_account:
            user = db.session.get(User, oauth_account.user_id)

            if not user:
                flash("연결된 사용자 정보를 찾을 수 없습니다.")
                return redirect(url_for("main"))

            establish_login_session(user)

            return login_destination(user)

        # 같은 이메일로 일반회원 가입 이력이 있다면 구글 계정만 연결합니다.
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            db.session.add(
                OAuthAccount(
                    provider="google",
                    subject=subject,
                    user_id=existing_user.id,
                )
            )
            db.session.commit()

            establish_login_session(existing_user)

            return login_destination(existing_user)

        # 완전한 신규 회원이면 아직 User를 생성하지 않고
        # 닉네임 설정 화면으로 이동시킵니다.
        session.clear()
        session["pending_social_signup"] = {
            "provider": "google",
            "subject": subject,
            "email": email,
            "suggested_name": google_name,
        }

        return redirect(url_for("social_nickname_setup"))

    @app.route("/social/nickname", methods=["GET", "POST"])
    def social_nickname_setup():
        pending_signup = session.get("pending_social_signup")

        if not pending_signup:
            flash("소셜 로그인 정보가 만료되었습니다. 다시 로그인해 주세요.")
            return redirect(url_for("main"))

        if request.method == "GET":
            return render_template(
                "social_nickname.html",
                suggested_name=pending_signup.get("suggested_name", ""),
                email=pending_signup.get("email", ""),
            )

        username = request.form.get("username", "").strip()

        if len(username) < 2:
            flash("닉네임은 2자 이상 입력해 주세요.")
            return redirect(url_for("social_nickname_setup"))

        if len(username) > 20:
            flash("닉네임은 20자 이하로 입력해 주세요.")
            return redirect(url_for("social_nickname_setup"))

        # 한글, 영어, 숫자, 밑줄만 허용합니다.
        if not re.fullmatch(r"[0-9A-Za-z가-힣_]+", username):
            flash("닉네임에는 한글, 영어, 숫자, 밑줄만 사용할 수 있습니다.")
            return redirect(url_for("social_nickname_setup"))

        duplicate_user = User.query.filter_by(username=username).first()

        if duplicate_user:
            flash("이미 사용 중인 닉네임입니다.")
            return redirect(url_for("social_nickname_setup"))

        provider = pending_signup.get("provider")
        subject = pending_signup.get("subject")
        email = pending_signup.get("email")

        if not provider or not subject or not email:
            session.pop("pending_social_signup", None)
            flash("소셜 로그인 정보가 올바르지 않습니다. 다시 로그인해 주세요.")
            return redirect(url_for("main"))

        # 중복 요청이나 뒤로가기 상황을 다시 검사합니다.
        existing_oauth_account = OAuthAccount.query.filter_by(
            provider=provider,
            subject=subject,
        ).first()

        if existing_oauth_account:
            user = db.session.get(User, existing_oauth_account.user_id)

            session.clear()

            if not user:
                flash("연결된 사용자 정보를 찾을 수 없습니다.")
                return redirect(url_for("main"))

            establish_login_session(user)

            return login_destination(user)

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(
                secrets.token_urlsafe(32)
            ),
        )

        db.session.add(user)
        db.session.flush()

        db.session.add(
            OAuthAccount(
                provider=provider,
                subject=subject,
                user_id=user.id,
            )
        )

        db.session.commit()

        establish_login_session(user)

        flash(f"{username}님, 가입을 환영합니다.")

        # 신규 회원은 학교 등록 화면으로 보냅니다.
        return redirect(url_for("main_success"))

    @app.post("/logout")
    def logout():
        session.clear()
        flash("로그아웃되었습니다.")
        return redirect(url_for("main"))

    @app.route("/signup", methods=["POST"])
    @rate_limit(limit=5, window=3600, scope="signup")
    def signup():
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("모든 항목을 입력해 주세요.")
            return redirect(url_for("login2"))

        if len(username) < 2:
            flash("이름은 2자 이상 입력해 주세요.")
            return redirect(url_for("login2"))

        if len(username) > 50:
            flash("이름은 50자 이하로 입력해 주세요.")
            return redirect(url_for("login2"))

        if len(password) < 8:
            flash("비밀번호는 8자 이상 입력해 주세요.")
            return redirect(url_for("login2"))

        # 이메일만 중복 가입을 차단합니다.
        if User.query.filter_by(email=email).first():
            flash("입력한 가입 정보를 사용할 수 없습니다.")
            return redirect(url_for("login2"))

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
        )

        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("회원가입 저장 실패")
            flash("회원가입 처리 중 오류가 발생했습니다.")
            return redirect(url_for("login2"))

        establish_login_session(user)

        flash("회원가입과 로그인이 완료되었습니다.")
        return redirect(url_for("main_success"))

    @app.cli.command("run-executive-election")
    def run_executive_election_command():
        """Run privilege-changing annual maintenance explicitly, never at web startup."""
        from pybo.executive_election import check_and_run_annual_election

        check_and_run_annual_election()
        audit_event("executive_election_run")
        print("Executive election maintenance completed.")

    @app.cli.command("encrypt-stored-credentials")
    def encrypt_stored_credentials_command():
        """Encrypt legacy plaintext OAuth credentials in place."""
        updated = 0
        for credential in GmailCredential.query.all():
            encrypted = encrypt_secret(app.config, credential.refresh_token)
            if encrypted != credential.refresh_token:
                credential.refresh_token = encrypted
                updated += 1
        db.session.commit()
        print(f"Encrypted {updated} stored credential(s).")

    return app
