from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, or_
from pybo import db
from pybo.models import (
    User,
    UserSchool,
    BoardPost,
    BoardComment,
    ExecutiveApplication,
)


def _get_executive_user_ids():
    """config에 등록된 고정 관리자 ID 목록을 가져옵니다."""
    try:
        return set(current_app.config.get("EXECUTIVE_USER_IDS", []))
    except Exception:
        return set()


def revoke_inactive_executives(days=90):
    """
    미접속 3개월(90일) 이상 된 임원의 임원 권한을 자동으로 박탈/탈퇴 처리합니다.
    (고정 관리자 제외)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    executives = User.query.filter_by(is_executive=True).all()
    fixed_admin_ids = _get_executive_user_ids()
    revoked_users = []

    for user in executives:
        if user.id in fixed_admin_ids:
            continue

        last_active = user.last_active_at or user.last_login_at or user.create_date
        if not last_active or last_active < cutoff_date:
            user.is_executive = False
            user.executive_elected_at = None
            revoked_users.append(user)

    if revoked_users:
        db.session.commit()

    return revoked_users


def calculate_user_scores(school_name, year=None):
    """
    특정 학교의 회원별 연간 활동 점수를 계산합니다.
    - 게시글 작성: 3점
    - 댓글 작성: 2점
    - 사랑별(좋아요) 수: 1점
    """
    if year is None:
        year = datetime.utcnow().year

    # 학교 소속 유저 목록
    users = (
        db.session.query(User)
        .outerjoin(UserSchool, UserSchool.user_id == User.id)
        .filter(
            or_(
                User.school_name == school_name,
                UserSchool.school_name == school_name,
            )
        )
        .distinct()
        .all()
    )

    cutoff_date = datetime.utcnow() - timedelta(days=90)  # 최근 3개월(90일) 이내 활동 유저
    scores = []

    for user in users:
        # 3개월 미접속/미활동 유저는 자동 선출 제외 (고정 관리자 제외)
        last_active = user.last_active_at or user.last_login_at or user.create_date
        if user.id not in _get_executive_user_ids() and (not last_active or last_active < cutoff_date):
            continue

        # 게시글 수 점수
        post_count = BoardPost.query.filter_by(
            user_id=user.id, school_name=school_name
        ).count()
        activity_score = post_count * 3

        # 댓글 수 점수
        comment_count = BoardComment.query.filter_by(
            user_id=user.id, school_name=school_name
        ).count()
        comment_score = comment_count * 2

        # 좋아요(사랑별) 점수: 유저가 쓴 글의 좋아요 합계
        user_posts = BoardPost.query.filter_by(
            user_id=user.id, school_name=school_name
        ).all()
        like_count = sum(len(post.voters) for post in user_posts)
        like_score = like_count * 1

        total_score = activity_score + comment_score + like_score

        scores.append(
            {
                "user": user,
                "school_name": school_name,
                "election_year": year,
                "activity_score": activity_score,
                "comment_score": comment_score,
                "like_score": like_score,
                "total_score": total_score,
            }
        )

    # 총점 내림차순 정렬
    scores.sort(key=lambda x: x["total_score"], reverse=True)
    return scores


def run_annual_executive_election(year=None):
    """
    매년 학교별 활동 점수 1위 회원을 임원으로 자동 선출합니다.
    """
    if year is None:
        year = datetime.utcnow().year

    executive_ids = _get_executive_user_ids()

    # 먼저 3개월 미접속 임원 권한 박탈 수행
    revoke_inactive_executives(days=90)

    # 등록된 모든 학교 목록 추출
    school_names = [
        r[0]
        for r in db.session.query(UserSchool.school_name)
        .filter(UserSchool.school_name.isnot(None))
        .distinct()
        .all()
    ]
    user_school_names = [
        r[0]
        for r in db.session.query(User.school_name)
        .filter(User.school_name.isnot(None))
        .distinct()
        .all()
    ]
    all_schools = list(set(school_names + user_school_names))

    elected_user_ids = set()

    for school_name in all_schools:
        scores = calculate_user_scores(school_name, year=year)
        if not scores:
            continue

        top_candidate = scores[0]
        winner = top_candidate["user"]

        # 0점이 아니거나 후보가 있는 경우 선출
        if top_candidate["total_score"] >= 0:
            winner.is_executive = True
            winner.executive_elected_at = datetime.utcnow()
            elected_user_ids.add(winner.id)

            # ExecutiveApplication DB 기록 생성 또는 갱신
            app_record = ExecutiveApplication.query.filter_by(
                user_id=winner.id,
                school_name=school_name,
                election_year=year,
            ).first()

            if not app_record:
                app_record = ExecutiveApplication(
                    user_id=winner.id,
                    school_name=school_name,
                    election_year=year,
                    status="accepted",
                    activity_score=top_candidate["activity_score"],
                    comment_score=top_candidate["comment_score"],
                    like_score=top_candidate["like_score"],
                )
                db.session.add(app_record)
            else:
                app_record.status = "accepted"
                app_record.activity_score = top_candidate["activity_score"]
                app_record.comment_score = top_candidate["comment_score"]
                app_record.like_score = top_candidate["like_score"]

    # 3개월 이상 미접속 또는 이번 선출에서 제외된 회원 권한 정리 (고정 관리자 제외)
    all_executives = User.query.filter_by(is_executive=True).all()
    for user in all_executives:
        if user.id in executive_ids:
            continue
        if user.id not in elected_user_ids:
            user.is_executive = False
            user.executive_elected_at = None

    db.session.commit()
    return list(elected_user_ids)


def check_and_run_annual_election():
    """상시로 3개월 미접속 임원 권한 박탈 및 연도별 자동 선출을 실행합니다."""
    # 1. 상시 미접속 3개월 임원 권한 박탈
    try:
        revoke_inactive_executives(days=90)
    except Exception as e:
        db.session.rollback()
        print(f"[Executive Revoke Warning] {e}")

    # 2. 연도별 자동 선출 검사
    current_year = datetime.utcnow().year
    existing = ExecutiveApplication.query.filter_by(
        election_year=current_year, status="accepted"
    ).first()

    if not existing:
        try:
            run_annual_executive_election(current_year)
        except Exception as e:
            db.session.rollback()
            print(f"[Executive Election Warning] {e}")
