from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from pybo import db, login_required
from pybo.models import AlbumComment, AlbumPhoto


bp = Blueprint("album", __name__, url_prefix="/album")


FACES_DATA = {
    1: [
        {"grad_face_num": 1, "top": "231px", "left": "71px"},
        {"grad_face_num": 2, "top": "223px", "left": "177px"},
        {"grad_face_num": 3, "top": "227px", "left": "274px"},
        {"grad_face_num": 4, "top": "226px", "left": "368px"},
        {"grad_face_num": 5, "top": "362px", "left": "68px"},
        {"grad_face_num": 6, "top": "356px", "left": "173px"},
        {"grad_face_num": 7, "top": "361px", "left": "271px"},
        {"grad_face_num": 8, "top": "358px", "left": "372px"},
    ],
    2: [
        {"grad_face_num": 1, "top": "247px", "left": "102px"},
        {"grad_face_num": 2, "top": "264px", "left": "175px"},
        {"grad_face_num": 3, "top": "302px", "left": "240px"},
        {"grad_face_num": 4, "top": "291px", "left": "311px"},
        {"grad_face_num": 5, "top": "451px", "left": "145px"},
        {"grad_face_num": 6, "top": "449px", "left": "227px"},
        {"grad_face_num": 7, "top": "482px", "left": "351px"},
    ],
    3: [
        {"grad_face_num": 1, "top": "190px", "left": "75px"},
        {"grad_face_num": 2, "top": "186px", "left": "176px"},
        {"grad_face_num": 3, "top": "191px", "left": "281px"},
        {"grad_face_num": 4, "top": "193px", "left": "384px"},
        {"grad_face_num": 5, "top": "334px", "left": "65px"},
        {"grad_face_num": 6, "top": "341px", "left": "174px"},
        {"grad_face_num": 7, "top": "339px", "left": "281px"},
        {"grad_face_num": 8, "top": "342px", "left": "384px"},
    ],
    4: [
        {"grad_face_num": 1, "top": "231px", "left": "71px"},
        {"grad_face_num": 2, "top": "223px", "left": "177px"},
        {"grad_face_num": 3, "top": "227px", "left": "274px"},
    ],
    5: [
        {"grad_face_num": 1, "top": "231px", "left": "71px"},
        {"grad_face_num": 2, "top": "223px", "left": "177px"},
    ],
}


def _executive_ids():
    return set(current_app.config.get("EXECUTIVE_USER_IDS", []))


@bp.route("/")
@login_required
def graduation_album():
    photo_registry = {
        photo.slot_class: photo.image_url for photo in AlbumPhoto.query.all()
    }

    return render_template(
        "graduation_album.html",
        faces_data=FACES_DATA,
        photo_registry=photo_registry,
        is_executive=session.get("user_id") in _executive_ids(),
    )


@bp.route("/cover")
@login_required
def album_cover():
    return render_template("album_cover.html")


@bp.route("/login")
def login_view():
    return redirect(url_for("main"))


@bp.route("/api/faces/<int:album_id>")
def get_faces(album_id):
    faces = FACES_DATA.get(album_id)
    if faces is None:
        return jsonify(status="error", message="앨범을 찾을 수 없습니다."), 404
    return jsonify(status="success", faces=faces)


@bp.post("/api/executive/upload-photo")
def upload_executive_photo():
    if session.get("user_id") not in _executive_ids():
        return jsonify(status="error", message="임원 권한이 필요합니다."), 403

    image = request.files.get("image")
    slot_class = request.form.get("slot_class", "").strip()
    allowed_extensions = {"jpg", "jpeg", "png", "webp", "gif"}

    if not image or not slot_class:
        return jsonify(status="error", message="사진과 슬롯 정보가 필요합니다."), 400

    original_name = secure_filename(image.filename or "")
    extension = Path(original_name).suffix.lower().lstrip(".")
    if extension not in allowed_extensions:
        return jsonify(status="error", message="지원하지 않는 이미지 형식입니다."), 400

    upload_directory = Path(current_app.static_folder) / "uploads"
    upload_directory.mkdir(parents=True, exist_ok=True)
    saved_name = f"album_{uuid4().hex}.{extension}"
    image.save(upload_directory / saved_name)
    image_url = url_for("static", filename=f"uploads/{saved_name}")

    photo = AlbumPhoto.query.filter_by(slot_class=slot_class).first()
    if photo:
        photo.image_url = image_url
    else:
        db.session.add(AlbumPhoto(slot_class=slot_class, image_url=image_url))

    db.session.commit()
    return jsonify(
        status="success",
        slot_class=slot_class,
        uploaded_image_url=image_url,
    )


@bp.route("/api/comments/<int:room_id>", methods=["GET", "POST"])
def comments_api(room_id):
    if room_id not in FACES_DATA:
        return jsonify(status="error", message="앨범을 찾을 수 없습니다."), 404

    if request.method == "GET":
        comments = (
            AlbumComment.query.filter_by(room_id=room_id)
            .order_by(AlbumComment.create_date.asc())
            .all()
        )
        return jsonify(
            status="success",
            comments=[
                {
                    "id": comment.id,
                    "text": comment.text,
                    "create_date": comment.create_date.isoformat(),
                }
                for comment in comments
            ],
        )

    if not session.get("user_id"):
        return jsonify(status="error", message="로그인이 필요합니다."), 401

    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify(status="error", message="댓글 내용을 입력해 주세요."), 400
    if len(text) > 500:
        return jsonify(status="error", message="댓글은 500자 이하로 입력해 주세요."), 400

    comment = AlbumComment(
        room_id=room_id,
        text=text,
        user_id=session["user_id"],
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify(
        status="success",
        comment={
            "id": comment.id,
            "text": comment.text,
            "create_date": comment.create_date.isoformat(),
        },
    )
