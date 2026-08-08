"""create shared classroom rooms

Revision ID: p38g9c5d1e08
Revises: o27f8b4c0d97
"""

from alembic import op
import sqlalchemy as sa

revision = "p38g9c5d1e08"
down_revision = "o27f8b4c0d97"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "classroom_room",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("create_date", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_classroom_room_owner_id", "classroom_room", ["owner_id"])
    op.create_index("ix_classroom_room_is_active", "classroom_room", ["is_active"])
    op.create_table(
        "classroom_participant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("slot_number", sa.Integer(), nullable=False),
        sa.Column("invited_at", sa.DateTime(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("slot_number >= 1 AND slot_number <= 8", name="ck_classroom_slot_range"),
        sa.ForeignKeyConstraint(["room_id"], ["classroom_room.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("room_id", "user_id", name="uq_classroom_room_user"),
        sa.UniqueConstraint("room_id", "slot_number", name="uq_classroom_room_slot"),
    )
    op.create_index("ix_classroom_participant_room_id", "classroom_participant", ["room_id"])
    op.create_index("ix_classroom_participant_user_id", "classroom_participant", ["user_id"])
    op.create_table(
        "classroom_message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=200), nullable=False),
        sa.Column("create_date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["classroom_room.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["user.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_classroom_message_room_id", "classroom_message", ["room_id"])
    op.create_index("ix_classroom_message_sender_id", "classroom_message", ["sender_id"])
    op.create_index("ix_classroom_message_create_date", "classroom_message", ["create_date"])


def downgrade():
    op.drop_table("classroom_message")
    op.drop_table("classroom_participant")
    op.drop_table("classroom_room")
