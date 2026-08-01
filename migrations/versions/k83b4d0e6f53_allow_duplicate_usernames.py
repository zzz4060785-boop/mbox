"""allow duplicate usernames

Revision ID: k83b4d0e6f53
Revises: j72a3c9d5e42
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "k83b4d0e6f53"
down_revision = "j72a3c9d5e42"
branch_labels = None
depends_on = None


NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade():
    username_constraint = next(
        constraint
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints("user")
        if constraint["column_names"] == ["username"]
    )
    constraint_name = username_constraint["name"] or "uq_user_username"

    with op.batch_alter_table(
        "user", naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint(constraint_name, type_="unique")


def downgrade():
    with op.batch_alter_table(
        "user", naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.create_unique_constraint("uq_user_username", ["username"])
