"""create notification table

Revision ID: e26b8d4a5c93
Revises: d15a9c7f3b82
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "e26b8d4a5c93"
down_revision = "d15a9c7f3b82"
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "notification" in tables:
        return
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("message", sa.String(length=300), nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "create_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["user.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_notification_user_id", "notification", ["user_id"])
    op.create_index("ix_notification_actor_id", "notification", ["actor_id"])
    op.create_index("ix_notification_kind", "notification", ["kind"])
    op.create_index("ix_notification_is_read", "notification", ["is_read"])
    op.create_index(
        "ix_notification_create_date",
        "notification",
        ["create_date"],
    )


def downgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "notification" in tables:
        op.drop_table("notification")
