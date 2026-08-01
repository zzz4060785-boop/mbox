"""add social privacy and album threads

Revision ID: d3a9f2c8e741
Revises: ab6f4b1c2a38
Create Date: 2026-07-31

개인정보 설정, 앨범 답글, 싫어요 기능을 배포합니다.
앱의 기존 자동 보강 로직으로 일부 항목이 이미 생긴 DB에서도
중복 칼럼/테이블 오류가 나지 않도록 존재 여부를 먼저 확인합니다.
"""

from alembic import op
import sqlalchemy as sa


revision = "d3a9f2c8e741"
down_revision = "ab6f4b1c2a38"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_names():
    return set(_inspector().get_table_names())


def _column_names(table_name):
    if table_name not in _table_names():
        return set()
    return {
        column["name"]
        for column in _inspector().get_columns(table_name)
    }


def _index_names(table_name):
    if table_name not in _table_names():
        return set()
    return {
        index["name"]
        for index in _inspector().get_indexes(table_name)
        if index.get("name")
    }


def upgrade():
    user_columns = _column_names("user")
    user_additions = (
        sa.Column("profile_image_url", sa.String(length=255), nullable=True),
        sa.Column(
            "tag_permission",
            sa.String(length=20),
            nullable=False,
            server_default="friends",
        ),
        sa.Column(
            "allow_album_comments",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "allow_connection_discovery",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "allow_messages",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "is_profile_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    for column in user_additions:
        if column.name not in user_columns:
            op.add_column("user", column)

    if "user_album_comment" in _table_names():
        comment_columns = _column_names("user_album_comment")
        if "parent_id" not in comment_columns:
            # SQLite에서도 자기참조 외래키를 안전하게 만들도록 batch 사용.
            with op.batch_alter_table("user_album_comment") as batch_op:
                batch_op.add_column(
                    sa.Column("parent_id", sa.Integer(), nullable=True)
                )
                batch_op.create_foreign_key(
                    "fk_user_album_comment_parent_id",
                    "user_album_comment",
                    ["parent_id"],
                    ["id"],
                    ondelete="CASCADE",
                )
        if (
            "ix_user_album_comment_parent_id"
            not in _index_names("user_album_comment")
        ):
            op.create_index(
                "ix_user_album_comment_parent_id",
                "user_album_comment",
                ["parent_id"],
                unique=False,
            )

    if "user_album_dislike" not in _table_names():
        op.create_table(
            "user_album_dislike",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("photo_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "create_date",
                sa.DateTime(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["photo_id"],
                ["user_album_photo.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["user.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "photo_id",
                "user_id",
                name="uq_user_album_dislike_photo_user",
            ),
        )
        op.create_index(
            "ix_user_album_dislike_photo_id",
            "user_album_dislike",
            ["photo_id"],
            unique=False,
        )
        op.create_index(
            "ix_user_album_dislike_user_id",
            "user_album_dislike",
            ["user_id"],
            unique=False,
        )


def downgrade():
    if "user_album_dislike" in _table_names():
        op.drop_table("user_album_dislike")

    if "user_album_comment" in _table_names():
        if "ix_user_album_comment_parent_id" in _index_names(
            "user_album_comment"
        ):
            op.drop_index(
                "ix_user_album_comment_parent_id",
                table_name="user_album_comment",
            )
        if "parent_id" in _column_names("user_album_comment"):
            with op.batch_alter_table("user_album_comment") as batch_op:
                batch_op.drop_column("parent_id")

    removable_user_columns = (
        "is_profile_public",
        "allow_messages",
        "allow_connection_discovery",
        "allow_album_comments",
        "tag_permission",
        "profile_image_url",
    )
    for column_name in removable_user_columns:
        if column_name in _column_names("user"):
            with op.batch_alter_table("user") as batch_op:
                batch_op.drop_column(column_name)
