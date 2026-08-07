import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_local_env():
    """Load simple KEY=VALUE entries without an extra dependency."""
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8-sig") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


_load_local_env()


def _database_uri():
    """Return the deployment database URL, with SQLite as a local fallback."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        # Some hosting providers still expose SQLAlchemy's legacy scheme.
        if database_url.startswith("postgres://"):
            database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
        elif database_url.startswith("postgresql://"):
            database_url = (
                "postgresql+psycopg://"
                + database_url[len("postgresql://"):]
            )
        return database_url
    return "sqlite:///" + os.path.join(BASE_DIR, "friendary.db")


DATABASE_URI = _database_uri()


class Config:
    SQLALCHEMY_DATABASE_URI = DATABASE_URI

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = (
        {}
        if DATABASE_URI.startswith("sqlite:")
        else {
            "pool_pre_ping": True,
            "pool_recycle": 1800,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "5")),
        }
    )
    # 개발 중 HTML·CSS·JS 수정 결과가 이전 캐시에 가려지지 않게 합니다.
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-key")
    # 게시글/공지 이미지 업로드 요청은 최대 10MB까지만 허용합니다.
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv(
        "SESSION_COOKIE_SECURE", ""
    ).lower() in {"1", "true", "yes"}
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "http")
    # Keep signed-in users logged in unless they opt out or explicitly log out.
    # Flask refreshes this rolling lifetime on active permanent sessions.
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    SESSION_REFRESH_EACH_REQUEST = True
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
    GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
    GMAIL_REDIRECT_URI = os.getenv(
        "GMAIL_REDIRECT_URI",
        "http://127.0.0.1:5000/google/gmail/callback",
    )
    GMAIL_ADMIN_EMAIL = os.getenv(
        "GMAIL_ADMIN_EMAIL",
        "junyoungkim355@gmail.com",
    )
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
    KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
    KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
    # 카카오 로컬(장소 검색) API는 로그인과 같은 REST API 키를 사용합니다.
    KAKAO_REST_API_KEY = os.getenv(
        "KAKAO_REST_API_KEY",
        os.getenv("KAKAO_CLIENT_ID", ""),
    )
    NEIS_API_KEY = os.getenv("NEIS_API_KEY", "")
    UNIVERSITY_API_KEY = os.getenv("UNIVERSITY_API_KEY", "")

    # 공지사항·앨범을 관리할 임원 계정의 user.id 목록입니다.
    # 여러 명이면 실행 환경에서 EXECUTIVE_USER_IDS=1,3,7 형태로 지정하세요.
    EXECUTIVE_USER_IDS = [
        int(user_id)
        for user_id in os.getenv("EXECUTIVE_USER_IDS", "1").split(",")
        if user_id.strip().isdigit()
    ]

    # 전자상거래 통신판매업 사업자 정보 (웹사이트 하단 필수 표기사항)
    COMPANY_NAME = os.getenv("COMPANY_NAME", "프렌다이어리 (Friendary)")

    COMPANY_OWNER = os.getenv("COMPANY_OWNER", "대표자명")
    COMPANY_BIZ_NO = os.getenv("COMPANY_BIZ_NO", "000-00-00000")
    COMPANY_MAIL_ORDER_NO = os.getenv("COMPANY_MAIL_ORDER_NO", "통신판매업 신고 준비중")
    COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "사업장 소재지 입력 필요")
    COMPANY_PHONE = os.getenv("COMPANY_PHONE", "010-0000-0000")
    COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "junyoungkim355@gmail.com")
    COMPANY_ESCROW_INFO = os.getenv("COMPANY_ESCROW_INFO", "구매안전(에스크로) 서비스 가입")

    # 포트원(PortOne V2) 결제 연동 설정
    PORTONE_STORE_ID = os.getenv("PORTONE_STORE_ID", "store-e7be92f1-f1c4-4d22-b53e-1c78d4e75e79")
    PORTONE_API_SECRET = os.getenv("PORTONE_API_SECRET", "")
    PORTONE_CHANNEL_KEY = os.getenv("PORTONE_CHANNEL_KEY", "")


