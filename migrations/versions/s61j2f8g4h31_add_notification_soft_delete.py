"""add notification soft delete

Revision ID: s61j2f8g4h31
Revises: r50i1e7f3g20
"""

from alembic import op
import sqlalchemy as sa


revision = "s61j2f8g4h31"
down_revision = "r50i1e7f3g20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notification",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_notification_deleted_at",
        "notification",
        ["deleted_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_notification_deleted_at", table_name="notification")
    op.drop_column("notification", "deleted_at")
