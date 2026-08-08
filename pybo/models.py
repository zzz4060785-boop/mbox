from datetime import datetime, timezone

from pybo import db


class User(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(50),
        nullable=False,
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
    )

    password = db.Column(
        db.String(255),
        nullable=False,
    )

    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    school_name = db.Column(db.String(120), nullable=True)
    school_type = db.Column(db.String(30), nullable=True)
    school_year = db.Column(db.String(4), nullable=True)
    school_major = db.Column(db.String(100), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    nationality = db.Column(db.String(80), nullable=True)
    hobby = db.Column(db.String(200), nullable=True)
    # 인맥 프로필 맨 위 원형 영역에 표시할 대표사진입니다.
    profile_image_url = db.Column(db.String(255), nullable=True)
    # 내 정보 화면의 개인정보 공개 설정입니다.
    tag_permission = db.Column(
        db.String(20),
        nullable=False,
        default="friends",
    )
    allow_album_comments = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    allow_connection_discovery = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    allow_messages = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    is_profile_public = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    allow_friend_search = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    # 임원 권한과 마지막 활동일은 자동 선출·6개월 미접속 해제에 사용합니다.
    is_executive = db.Column(db.Boolean, nullable=False, default=False)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_active_at = db.Column(db.DateTime, nullable=True, index=True)
    executive_elected_at = db.Column(db.DateTime, nullable=True)
    sarangdal_balance = db.Column(db.Integer, nullable=False, default=1)
    last_sarangdal_month = db.Column(db.String(7), nullable=True)

    @property
    def is_executive_user(self):
        try:
            from flask import current_app
            executive_ids = set(current_app.config.get("EXECUTIVE_USER_IDS", []))
        except Exception:
            executive_ids = set()
        return bool(self.is_executive or (self.id in executive_ids))

    @property
    def display_name(self):
        if self.is_executive_user:
            return f"👑 {self.username}"
        return self.username



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    target_url = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    user = db.relationship("User", foreign_keys=[user_id])
    actor = db.relationship("User", foreign_keys=[actor_id])


class GmailCredential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    refresh_token = db.Column(db.Text, nullable=False)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SecurityRateLimit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_hash = db.Column(db.String(64), nullable=False)
    window_start = db.Column(db.BigInteger, nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("key_hash", "window_start", name="uq_security_rate_limit_window"),
        db.Index("ix_security_rate_limit_window_start", "window_start"),
    )


class SecurityIPBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    unknown_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    window_started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_attempt_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    blocked_at = db.Column(db.DateTime, nullable=True, index=True)


class VerificationChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    purpose = db.Column(db.String(30), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    consumed_at = db.Column(db.DateTime, nullable=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    user = db.relationship("User")


class SecurityAuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(60), nullable=False, index=True)
    ip_hash = db.Column(db.String(64), nullable=False, index=True)
    details = db.Column(db.Text, nullable=False, default="{}")
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )


class ExecutiveApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school_name = db.Column(db.String(120), nullable=False, index=True)
    election_year = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    activity_score = db.Column(db.Integer, nullable=False, default=0)
    comment_score = db.Column(db.Integer, nullable=False, default=0)
    like_score = db.Column(db.Integer, nullable=False, default=0)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "school_name",
            "election_year",
            name="uq_executive_application_user_school_year",
        ),
    )


class UserSchool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    school_name = db.Column(db.String(120), nullable=False, index=True)
    school_type = db.Column(db.String(30), nullable=False)
    school_year = db.Column(db.String(4), nullable=False)
    school_major = db.Column(db.String(100), nullable=True)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship("User")
    __table_args__ = (
        db.UniqueConstraint("user_id", "school_name", name="uq_user_school_membership"),
    )


class SchoolLeaveLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    school_name = db.Column(db.String(120), nullable=False)
    month_key = db.Column(db.String(7), nullable=False, index=True)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class OAuthAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(30), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "provider",
            "subject",
            name="uq_oauth_provider_subject",
        ),
    )


class AlbumPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_class = db.Column(db.String(80), unique=True, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class AlbumComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, nullable=False, index=True)
    text = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


# ─────────────────────────────────────────────────────────────
# 개인 앨범 피드: 사진, 좋아요, 댓글
# 아래 모델들은 "나의 앨범" 화면의 내용을 브라우저가 아닌 DB에 보관합니다.
# ─────────────────────────────────────────────────────────────
class UserAlbumPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(300), nullable=False, default="")
    school_name = db.Column(db.String(120), nullable=True, index=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    user = db.relationship("User")
    comments = db.relationship(
        "UserAlbumComment",
        backref="photo",
        cascade="all, delete-orphan",
        order_by="UserAlbumComment.create_date",
    )
    likes = db.relationship(
        "UserAlbumLike",
        backref="photo",
        cascade="all, delete-orphan",
    )
    dislikes = db.relationship(
        "UserAlbumDislike",
        backref="photo",
        cascade="all, delete-orphan",
    )


class AiImageUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month_key = db.Column(db.String(7), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="processing")
    style = db.Column(db.String(30), nullable=False)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User")

class UserAlbumLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(
        db.Integer,
        db.ForeignKey("user_album_photo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


class UserAlbumDislike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(
        db.Integer,
        db.ForeignKey("user_album_photo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "photo_id",
            "user_id",
            name="uq_user_album_dislike_photo_user",
        ),
    )


class UserAlbumComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(
        db.Integer,
        db.ForeignKey("user_album_photo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 부모 댓글을 가리켜 답글이 나뭇가지처럼 이어지게 합니다.
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("user_album_comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content = db.Column(db.String(500), nullable=False)
    school_name = db.Column(db.String(120), nullable=True, index=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    user = db.relationship("User")
    replies = db.relationship(
        "UserAlbumComment",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        order_by="UserAlbumComment.create_date",
        single_parent=True,
    )


# 친구 신청은 pending, 수락 후에는 accepted 상태가 됩니다.
class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(20), nullable=False, default="pending")
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    accepted_date = db.Column(db.DateTime, nullable=True)
    requester = db.relationship("User", foreign_keys=[requester_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

    __table_args__ = (
        db.UniqueConstraint(
            "requester_id",
            "receiver_id",
            name="uq_friendship_direction",
        ),
        db.CheckConstraint(
            "requester_id <> receiver_id",
            name="ck_friendship_not_self",
        ),
    )


class DirectMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = db.Column(db.String(1000), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])


class ClassroomRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    owner = db.relationship("User")
    participants = db.relationship(
        "ClassroomParticipant",
        back_populates="room",
        cascade="all, delete-orphan",
        order_by="ClassroomParticipant.slot_number",
    )
    messages = db.relationship(
        "ClassroomMessage",
        back_populates="room",
        cascade="all, delete-orphan",
    )


class ClassroomParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom_room.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_number = db.Column(db.Integer, nullable=False)
    invited_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    joined_at = db.Column(db.DateTime, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    room = db.relationship("ClassroomRoom", back_populates="participants")
    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("room_id", "user_id", name="uq_classroom_room_user"),
        db.UniqueConstraint("room_id", "slot_number", name="uq_classroom_room_slot"),
        db.CheckConstraint("slot_number >= 1 AND slot_number <= 8", name="ck_classroom_slot_range"),
    )


class ClassroomMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom_room.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = db.Column(db.String(200), nullable=False)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    room = db.relationship("ClassroomRoom", back_populates="messages")
    sender = db.relationship("User")


# ─────────────────────────────────────────────────────────────
# 우리들의 추천장소 게시판
# 맛집·장소·동창 가게 추천과 직접 홍보를 별도 관리합니다.
# ─────────────────────────────────────────────────────────────
class RecommendationPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = db.Column(db.String(30), nullable=False)
    school_name = db.Column(db.String(120), nullable=True, index=True)
    place_name = db.Column(db.String(120), nullable=False)
    region = db.Column(db.String(120), nullable=False, default="")
    address = db.Column(db.String(255), nullable=False, default="")
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    price_range = db.Column(db.String(50), nullable=False, default="")
    external_url = db.Column(db.String(500), nullable=False, default="")
    map_url = db.Column(db.String(500), nullable=False, default="")
    tags = db.Column(db.String(500), nullable=False, default="")
    promotion_type = db.Column(
        db.String(20),
        nullable=False,
        default="review",
    )
    views = db.Column(db.Integer, nullable=False, default=0)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    modify_date = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User")
    media = db.relationship(
        "RecommendationMedia",
        backref="post",
        cascade="all, delete-orphan",
        order_by="RecommendationMedia.id",
    )
    comments = db.relationship(
        "RecommendationComment",
        backref="post",
        cascade="all, delete-orphan",
        order_by="RecommendationComment.create_date",
    )
    reactions = db.relationship(
        "RecommendationReaction",
        backref="post",
        cascade="all, delete-orphan",
    )


class RecommendationMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("recommendation_post.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_url = db.Column(db.String(500), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)


class RecommendationReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("recommendation_post.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reaction = db.Column(db.String(10), nullable=False)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_recommendation_reaction_post_user",
        ),
    )


class RecommendationComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("recommendation_post.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("recommendation_comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content = db.Column(db.String(1000), nullable=False)
    school_name = db.Column(db.String(120), nullable=True, index=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    user = db.relationship("User")
    replies = db.relationship(
        "RecommendationComment",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        order_by="RecommendationComment.create_date",
        single_parent=True,
    )


class BoardNotice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(
        db.String(120),
        nullable=True,
        index=True,
    )
    content = db.Column(db.String(300), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    media_type = db.Column(
        db.String(20),
        nullable=False,
        default="image",
    )
    original_name = db.Column(db.String(255), nullable=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    modify_date = db.Column(db.DateTime, nullable=True)


class BoardPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    school_name = db.Column(db.String(120), nullable=True, index=True)
    views = db.Column(db.Integer, nullable=False, default=0)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    modify_date = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User", foreign_keys=[user_id])
    voters = db.relationship(
        "User",
        secondary="board_post_voter",
        backref=db.backref("voted_board_posts", lazy="dynamic"),
    )


class BoardPostMeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("board_post.id"),
        unique=True,
        nullable=False,
    )
    tags = db.Column(db.String(500), nullable=False, default="")
    is_secret = db.Column(db.Boolean, nullable=False, default=False)


class BoardAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("board_post.id"),
        nullable=False,
        index=True,
    )
    file_url = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    media_type = db.Column(
        db.String(20),
        nullable=False,
        default="image",
    )


board_post_voter = db.Table(
    "board_post_voter",
    db.Column(
        "post_id",
        db.Integer,
        db.ForeignKey("board_post.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


board_comment_voter = db.Table(
    "board_comment_voter",
    db.Column(
        "comment_id",
        db.Integer,
        db.ForeignKey("board_comment.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class BoardComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("board_post.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )
    content = db.Column(db.Text, nullable=False)
    school_name = db.Column(db.String(120), nullable=True, index=True)
    create_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    modify_date = db.Column(db.DateTime, nullable=True)
    post = db.relationship(
        "BoardPost",
        backref=db.backref(
            "comments",
            cascade="all, delete-orphan",
            order_by="BoardComment.create_date",
        ),
    )
    user = db.relationship("User")
    voters = db.relationship(
        "User",
        secondary=board_comment_voter,
        backref=db.backref("voted_board_comments", lazy="dynamic"),
    )


class PaymentOrder(db.Model):
    __tablename__ = "payment_order"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    order_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="READY", index=True)
    pay_method = db.Column(db.String(50), nullable=True)
    tx_id = db.Column(db.String(100), nullable=True)
    receipt_url = db.Column(db.String(500), nullable=True)
    sarangdal_count = db.Column(db.Integer, nullable=False, default=0)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User")


class GooglePlayPurchase(db.Model):
    __tablename__ = "google_play_purchase"

    id = db.Column(db.Integer, primary_key=True)
    purchase_token = db.Column(db.String(1024), unique=True, nullable=False, index=True)
    product_id = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = db.Column(db.String(200), nullable=True, index=True)
    sarangdal_count = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="VERIFIED", index=True)
    purchase_time_ms = db.Column(db.BigInteger, nullable=True)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User")

