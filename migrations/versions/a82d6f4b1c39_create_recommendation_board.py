"""create recommendation board

Revision ID: a82d6f4b1c39
Revises: f4b7c1d92e06
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "a82d6f4b1c39"
down_revision = "f4b7c1d92e06"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    tables = _tables()
    if "recommendation_post" not in tables:
        op.create_table(
            "recommendation_post",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=30), nullable=False),
            sa.Column("place_name", sa.String(length=120), nullable=False),
            sa.Column("region", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("address", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("price_range", sa.String(length=50), nullable=False, server_default=""),
            sa.Column("external_url", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("map_url", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("tags", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("promotion_type", sa.String(length=20), nullable=False, server_default="review"),
            sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("create_date", sa.DateTime(), nullable=False),
            sa.Column("modify_date", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_recommendation_post_user_id", "recommendation_post", ["user_id"])
        op.create_index(
            "ix_recommendation_search",
            "recommendation_post",
            ["category", "region", "create_date"],
        )

    if "recommendation_media" not in tables:
        op.create_table(
            "recommendation_media",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("file_url", sa.String(length=500), nullable=False),
            sa.Column("media_type", sa.String(length=20), nullable=False),
            sa.Column("original_name", sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["recommendation_post.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_recommendation_media_post_id", "recommendation_media", ["post_id"])

    if "recommendation_reaction" not in tables:
        op.create_table(
            "recommendation_reaction",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("reaction", sa.String(length=10), nullable=False),
            sa.Column("create_date", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["recommendation_post.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("post_id", "user_id", name="uq_recommendation_reaction_post_user"),
        )
        op.create_index("ix_recommendation_reaction_post_id", "recommendation_reaction", ["post_id"])
        op.create_index("ix_recommendation_reaction_user_id", "recommendation_reaction", ["user_id"])

    if "recommendation_comment" not in tables:
        op.create_table(
            "recommendation_comment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("content", sa.String(length=1000), nullable=False),
            sa.Column("create_date", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["recommendation_comment.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["post_id"], ["recommendation_post.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_recommendation_comment_post_id", "recommendation_comment", ["post_id"])
        op.create_index("ix_recommendation_comment_user_id", "recommendation_comment", ["user_id"])
        op.create_index("ix_recommendation_comment_parent_id", "recommendation_comment", ["parent_id"])


def downgrade():
    tables = _tables()
    for table_name in (
        "recommendation_comment",
        "recommendation_reaction",
        "recommendation_media",
        "recommendation_post",
    ):
        if table_name in tables:
            op.drop_table(table_name)
