"""create ai image usage table

Revision ID: i61f2b8d4c31
Revises: h59e1a7c3b20
"""

from alembic import op
import sqlalchemy as sa


revision = "i61f2b8d4c31"
down_revision = "h59e1a7c3b20"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "ai_image_usage" in inspector.get_table_names():
        return
    op.create_table(
        "ai_image_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("month_key", sa.String(length=7), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("style", sa.String(length=30), nullable=False),
        sa.Column("create_date", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "month_key", name="uq_ai_image_user_month"),
    )
    op.create_index("ix_ai_image_usage_user_id", "ai_image_usage", ["user_id"])
    op.create_index("ix_ai_image_usage_month_key", "ai_image_usage", ["month_key"])


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "ai_image_usage" in inspector.get_table_names():
        op.drop_table("ai_image_usage")
