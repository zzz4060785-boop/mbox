"""add server-side verification challenges and session version

Revision ID: m05d6f2a8b75
Revises: l94c5e1f7a64
"""

from alembic import op
import sqlalchemy as sa


revision = "m05d6f2a8b75"
down_revision = "l94c5e1f7a64"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "verification_challenge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=True),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("create_date", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("token", name="uq_verification_challenge_token"),
    )
    op.create_index("ix_verification_challenge_token", "verification_challenge", ["token"], unique=True)
    op.create_index("ix_verification_challenge_purpose", "verification_challenge", ["purpose"])
    op.create_index("ix_verification_challenge_expires_at", "verification_challenge", ["expires_at"])


def downgrade():
    op.drop_table("verification_challenge")
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("session_version")
