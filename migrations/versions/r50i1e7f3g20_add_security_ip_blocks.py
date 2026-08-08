"""add security IP blocks

Revision ID: r50i1e7f3g20
Revises: q49h0d6e2f19
"""

from alembic import op
import sqlalchemy as sa


revision = "r50i1e7f3g20"
down_revision = "q49h0d6e2f19"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "security_ip_block",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("unknown_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("blocked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_security_ip_block_ip_hash", "security_ip_block", ["ip_hash"], unique=True)
    op.create_index("ix_security_ip_block_blocked_at", "security_ip_block", ["blocked_at"])


def downgrade():
    op.drop_index("ix_security_ip_block_blocked_at", table_name="security_ip_block")
    op.drop_index("ix_security_ip_block_ip_hash", table_name="security_ip_block")
    op.drop_table("security_ip_block")
