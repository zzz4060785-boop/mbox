"""create gmail credential table

Revision ID: g48d0f6c7e15
Revises: f37c9e5b6d04
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "g48d0f6c7e15"
down_revision = "f37c9e5b6d04"
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "gmail_credential" in tables:
        return
    op.create_table(
        "gmail_credential",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=120), nullable=False, unique=True),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("create_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("update_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    if "gmail_credential" in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table("gmail_credential")
