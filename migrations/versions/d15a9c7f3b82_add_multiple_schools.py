"""add multiple school memberships

Revision ID: d15a9c7f3b82
Revises: c04f8b6e2a71
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "d15a9c7f3b82"
down_revision = "c04f8b6e2a71"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name):
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade():
    tables = _tables()
    if "user_school" not in tables:
        op.create_table(
            "user_school",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("school_name", sa.String(length=120), nullable=False),
            sa.Column("school_type", sa.String(length=30), nullable=False),
            sa.Column("school_year", sa.String(length=4), nullable=False),
            sa.Column("school_major", sa.String(length=100), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("create_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "school_name", name="uq_user_school_membership"),
        )
        op.create_index("ix_user_school_user_id", "user_school", ["user_id"])
        op.create_index("ix_user_school_school_name", "user_school", ["school_name"])
    op.execute(sa.text(
        "INSERT OR IGNORE INTO user_school "
        "(user_id, school_name, school_type, school_year, school_major, is_primary, create_date) "
        "SELECT id, school_name, COALESCE(school_type, 'school'), "
        "COALESCE(school_year, '0000'), school_major, 1, CURRENT_TIMESTAMP "
        "FROM user WHERE school_name IS NOT NULL AND TRIM(school_name) <> ''"
    ))
    if "school_leave_log" not in tables:
        op.create_table(
            "school_leave_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("school_name", sa.String(length=120), nullable=False),
            sa.Column("month_key", sa.String(length=7), nullable=False),
            sa.Column("create_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_school_leave_log_user_id", "school_leave_log", ["user_id"])
        op.create_index("ix_school_leave_log_month_key", "school_leave_log", ["month_key"])

    authored_tables = (
        "board_post",
        "board_comment",
        "recommendation_post",
        "recommendation_comment",
        "user_album_photo",
        "user_album_comment",
    )
    for table_name in authored_tables:
        if table_name in _tables() and "school_name" not in _columns(table_name):
            op.add_column(table_name, sa.Column("school_name", sa.String(length=120), nullable=True))
    for table_name in authored_tables:
        if table_name in _tables() and "user_id" in _columns(table_name):
            op.execute(sa.text(
                f'UPDATE "{table_name}" SET school_name = '
                f'(SELECT school_name FROM user WHERE user.id = "{table_name}".user_id) '
                "WHERE school_name IS NULL"
            ))


def downgrade():
    for table_name in (
        "user_album_comment",
        "user_album_photo",
        "recommendation_comment",
        "recommendation_post",
        "board_comment",
        "board_post",
    ):
        if table_name in _tables() and "school_name" in _columns(table_name):
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_column("school_name")
    if "school_leave_log" in _tables():
        op.drop_table("school_leave_log")
    if "user_school" in _tables():
        op.drop_table("user_school")
