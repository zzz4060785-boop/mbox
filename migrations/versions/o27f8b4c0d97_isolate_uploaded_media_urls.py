"""serve uploaded media through isolated authenticated route

Revision ID: o27f8b4c0d97
Revises: n16e7a3b9c86
"""

from alembic import op
import sqlalchemy as sa

revision = "o27f8b4c0d97"
down_revision = "n16e7a3b9c86"
branch_labels = None
depends_on = None

URL_COLUMNS = (
    ("user", "profile_image_url"),
    ("album_photo", "image_url"),
    ("user_album_photo", "image_url"),
    ("board_notice", "image_url"),
    ("board_attachment", "file_url"),
    ("recommendation_media", "file_url"),
)


def _replace(old, new):
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table, column in URL_COLUMNS:
        if table not in tables:
            continue
        columns = {item["name"] for item in inspector.get_columns(table)}
        if column not in columns:
            continue
        op.execute(
            sa.text(
                f'UPDATE "{table}" SET "{column}" = replace("{column}", :old, :new) '
                f'WHERE "{column}" LIKE :pattern'
            ).bindparams(old=old, new=new, pattern=f"%{old}%")
        )


def upgrade():
    _replace("/static/uploads/", "/media/")


def downgrade():
    _replace("/media/", "/static/uploads/")
