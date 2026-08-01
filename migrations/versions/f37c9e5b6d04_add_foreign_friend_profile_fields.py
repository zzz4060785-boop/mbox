"""add foreign friend profile fields

Revision ID: f37c9e5b6d04
Revises: e26b8d4a5c93
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "f37c9e5b6d04"
down_revision = "e26b8d4a5c93"
branch_labels = None
depends_on = None


def _columns():
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("user")
    }


def upgrade():
    columns = _columns()
    if "nationality" not in columns:
        op.add_column(
            "user",
            sa.Column("nationality", sa.String(length=80), nullable=True),
        )
    if "hobby" not in columns:
        op.add_column(
            "user",
            sa.Column("hobby", sa.String(length=200), nullable=True),
        )


def downgrade():
    columns = _columns()
    with op.batch_alter_table("user") as batch_op:
        if "hobby" in columns:
            batch_op.drop_column("hobby")
        if "nationality" in columns:
            batch_op.drop_column("nationality")
