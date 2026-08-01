"""add board media types

Revision ID: b93e7a2d5f10
Revises: a82d6f4b1c39
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "b93e7a2d5f10"
down_revision = "a82d6f4b1c39"
branch_labels = None
depends_on = None


def _columns(table_name):
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {
        column["name"]
        for column in inspector.get_columns(table_name)
    }


def upgrade():
    notice_columns = _columns("board_notice")
    if "media_type" not in notice_columns:
        op.add_column(
            "board_notice",
            sa.Column(
                "media_type",
                sa.String(length=20),
                nullable=False,
                server_default="image",
            ),
        )
    if "original_name" not in notice_columns:
        op.add_column(
            "board_notice",
            sa.Column("original_name", sa.String(length=255), nullable=True),
        )

    attachment_columns = _columns("board_attachment")
    if "media_type" not in attachment_columns:
        op.add_column(
            "board_attachment",
            sa.Column(
                "media_type",
                sa.String(length=20),
                nullable=False,
                server_default="image",
            ),
        )


def downgrade():
    if "media_type" in _columns("board_attachment"):
        with op.batch_alter_table("board_attachment") as batch_op:
            batch_op.drop_column("media_type")
    for column_name in ("original_name", "media_type"):
        if column_name in _columns("board_notice"):
            with op.batch_alter_table("board_notice") as batch_op:
                batch_op.drop_column(column_name)
