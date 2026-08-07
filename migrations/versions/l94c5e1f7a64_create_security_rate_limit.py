"""create shared security rate limit table

Revision ID: l94c5e1f7a64
Revises: k83b4d0e6f53
"""

from alembic import op
import sqlalchemy as sa


revision = "l94c5e1f7a64"
down_revision = "k83b4d0e6f53"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "security_rate_limit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.BigInteger(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("key_hash", "window_start", name="uq_security_rate_limit_window"),
    )
    op.create_index("ix_security_rate_limit_window_start", "security_rate_limit", ["window_start"])


def downgrade():
    op.drop_index("ix_security_rate_limit_window_start", table_name="security_rate_limit")
    op.drop_table("security_rate_limit")
