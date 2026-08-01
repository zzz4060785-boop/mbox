"""add user last active timestamp

Revision ID: h59e1a7c3b20
Revises: g48d0f6c7e15
"""

from alembic import op
import sqlalchemy as sa


revision = "h59e1a7c3b20"
down_revision = "g48d0f6c7e15"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    column_names = {column["name"] for column in inspector.get_columns("user")}

    if "last_active_at" not in column_names:
        with op.batch_alter_table("user") as batch_op:
            batch_op.add_column(
                sa.Column("last_active_at", sa.DateTime(), nullable=True)
            )

    inspector = sa.inspect(op.get_bind())
    index_names = {index["name"] for index in inspector.get_indexes("user")}
    if "ix_user_last_active_at" not in index_names:
        with op.batch_alter_table("user") as batch_op:
            batch_op.create_index(
                "ix_user_last_active_at", ["last_active_at"], unique=False
            )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    index_names = {index["name"] for index in inspector.get_indexes("user")}
    column_names = {column["name"] for column in inspector.get_columns("user")}

    with op.batch_alter_table("user") as batch_op:
        if "ix_user_last_active_at" in index_names:
            batch_op.drop_index("ix_user_last_active_at")
        if "last_active_at" in column_names:
            batch_op.drop_column("last_active_at")
