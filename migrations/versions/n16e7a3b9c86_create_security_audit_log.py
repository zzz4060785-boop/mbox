"""create security audit log

Revision ID: n16e7a3b9c86
Revises: m05d6f2a8b75
"""

from alembic import op
import sqlalchemy as sa

revision = "n16e7a3b9c86"
down_revision = "m05d6f2a8b75"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "security_audit_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("details", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("create_date", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_security_audit_event_user_id", "security_audit_event", ["user_id"])
    op.create_index("ix_security_audit_event_event_type", "security_audit_event", ["event_type"])
    op.create_index("ix_security_audit_event_ip_hash", "security_audit_event", ["ip_hash"])
    op.create_index("ix_security_audit_event_create_date", "security_audit_event", ["create_date"])


def downgrade():
    op.drop_table("security_audit_event")
