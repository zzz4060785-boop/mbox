"""allow multiple AI image uses per user and month

Revision ID: j72a3c9d5e42
Revises: i61f2b8d4c31
"""

from alembic import op
import sqlalchemy as sa


revision = "j72a3c9d5e42"
down_revision = "i61f2b8d4c31"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "ai_image_usage" not in inspector.get_table_names():
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("ai_image_usage")
    }
    if "uq_ai_image_user_month" in unique_constraints:
        with op.batch_alter_table("ai_image_usage") as batch_op:
            batch_op.drop_constraint(
                "uq_ai_image_user_month",
                type_="unique",
            )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "ai_image_usage" not in inspector.get_table_names():
        return

    with op.batch_alter_table("ai_image_usage") as batch_op:
        batch_op.create_unique_constraint(
            "uq_ai_image_user_month",
            ["user_id", "month_key"],
        )
