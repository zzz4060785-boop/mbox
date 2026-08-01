"""add friend search profile fields

Revision ID: f4b7c1d92e06
Revises: d3a9f2c8e741
Create Date: 2026-07-31

친구 찾기의 나이·성별 필터와 검색 노출 설정을 추가합니다.
기존 자동 보강으로 칼럼이 존재하는 DB에서는 안전하게 건너뜁니다.
"""

from alembic import op
import sqlalchemy as sa


revision = "f4b7c1d92e06"
down_revision = "d3a9f2c8e741"
branch_labels = None
depends_on = None


def _user_columns():
    inspector = sa.inspect(op.get_bind())
    if "user" not in inspector.get_table_names():
        return set()
    return {
        column["name"]
        for column in inspector.get_columns("user")
    }


def upgrade():
    columns = _user_columns()
    additions = (
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column(
            "allow_friend_search",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    for column in additions:
        if column.name not in columns:
            op.add_column("user", column)

    # 이름·나이·학교·성별 복합 검색의 기본 필터 성능을 보강합니다.
    inspector = sa.inspect(op.get_bind())
    index_names = {
        index["name"]
        for index in inspector.get_indexes("user")
        if index.get("name")
    }
    if "ix_user_friend_search" not in index_names:
        op.create_index(
            "ix_user_friend_search",
            "user",
            [
                "allow_friend_search",
                "is_profile_public",
                "age",
                "gender",
                "school_name",
            ],
            unique=False,
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "user" not in inspector.get_table_names():
        return
    index_names = {
        index["name"]
        for index in inspector.get_indexes("user")
        if index.get("name")
    }
    if "ix_user_friend_search" in index_names:
        op.drop_index("ix_user_friend_search", table_name="user")

    for column_name in ("allow_friend_search", "gender", "age"):
        if column_name in _user_columns():
            with op.batch_alter_table("user") as batch_op:
                batch_op.drop_column(column_name)
