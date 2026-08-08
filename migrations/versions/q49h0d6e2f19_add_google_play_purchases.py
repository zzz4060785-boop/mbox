"""add google play purchases

Revision ID: q49h0d6e2f19
Revises: p38g9c5d1e08
"""

from alembic import op
import sqlalchemy as sa


revision = "q49h0d6e2f19"
down_revision = "p38g9c5d1e08"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "google_play_purchase",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_token", sa.String(length=1024), nullable=False),
        sa.Column("product_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.String(length=200), nullable=True),
        sa.Column("sarangdal_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("purchase_time_ms", sa.BigInteger(), nullable=True),
        sa.Column("create_date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_token"),
    )
    op.create_index("ix_google_play_purchase_order_id", "google_play_purchase", ["order_id"])
    op.create_index("ix_google_play_purchase_product_id", "google_play_purchase", ["product_id"])
    op.create_index("ix_google_play_purchase_purchase_token", "google_play_purchase", ["purchase_token"], unique=True)
    op.create_index("ix_google_play_purchase_status", "google_play_purchase", ["status"])
    op.create_index("ix_google_play_purchase_user_id", "google_play_purchase", ["user_id"])


def downgrade():
    op.drop_index("ix_google_play_purchase_user_id", table_name="google_play_purchase")
    op.drop_index("ix_google_play_purchase_status", table_name="google_play_purchase")
    op.drop_index("ix_google_play_purchase_purchase_token", table_name="google_play_purchase")
    op.drop_index("ix_google_play_purchase_product_id", table_name="google_play_purchase")
    op.drop_index("ix_google_play_purchase_order_id", table_name="google_play_purchase")
    op.drop_table("google_play_purchase")
