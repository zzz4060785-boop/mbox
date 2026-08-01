"""add executive elections

Revision ID: c04f8b6e2a71
Revises: b93e7a2d5f10
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "c04f8b6e2a71"
down_revision = "b93e7a2d5f10"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    user_columns = {column["name"] for column in inspector.get_columns("user")}
    additions = (
        ("is_executive", sa.Boolean(), False, sa.text("0")),
        ("last_login_at", sa.DateTime(), True, None),
        ("executive_elected_at", sa.DateTime(), True, None),
    )
    for name, column_type, nullable, default in additions:
        if name not in user_columns:
            op.add_column(
                "user",
                sa.Column(
                    name,
                    column_type,
                    nullable=nullable,
                    server_default=default,
                ),
            )
    op.execute(
        sa.text(
            "UPDATE user SET is_executive = 1, "
            "last_login_at = CURRENT_TIMESTAMP, "
            "executive_elected_at = CURRENT_TIMESTAMP WHERE id = 1"
        )
    )
    if "executive_application" not in inspector.get_table_names():
        op.create_table(
            "executive_application",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("school_name", sa.String(length=120), nullable=False),
            sa.Column("election_year", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("activity_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("comment_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("like_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("create_date", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "user_id", "school_name", "election_year",
                name="uq_executive_application_user_school_year",
            ),
        )
        op.create_index(
            "ix_executive_application_user_id",
            "executive_application",
            ["user_id"],
        )
        op.create_index(
            "ix_executive_application_school_name",
            "executive_application",
            ["school_name"],
        )
        op.create_index(
            "ix_executive_application_election_year",
            "executive_application",
            ["election_year"],
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "executive_application" in inspector.get_table_names():
        op.drop_table("executive_application")
    user_columns = {column["name"] for column in inspector.get_columns("user")}
    for name in ("executive_elected_at", "last_login_at", "is_executive"):
        if name in user_columns:
            with op.batch_alter_table("user") as batch_op:
                batch_op.drop_column(name)
