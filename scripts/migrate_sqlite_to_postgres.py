"""Copy an existing Friendary SQLite database into an empty PostgreSQL DB."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import Boolean, MetaData, create_engine, func, select, text

from pybo import create_app, db


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite_file", type=Path)
    return parser.parse_args()


def converted_row(row, target_table, common_columns):
    values = {}
    for name in common_columns:
        value = row[name]
        if value is not None and isinstance(target_table.c[name].type, Boolean):
            value = bool(value)
        values[name] = value
    return values


def main():
    args = parse_args()
    sqlite_file = args.sqlite_file.resolve()
    if not sqlite_file.is_file():
        raise SystemExit(f"SQLite file not found: {sqlite_file}")

    source_engine = create_engine(f"sqlite:///{sqlite_file.as_posix()}")
    source_metadata = MetaData()
    source_metadata.reflect(bind=source_engine)

    app = create_app()
    copied = {}
    with app.app_context():
        target_engine = db.engine
        if target_engine.dialect.name != "postgresql":
            raise SystemExit("DATABASE_URL must point to PostgreSQL.")

        with target_engine.connect() as target_connection:
            populated = []
            for table in db.metadata.sorted_tables:
                count = target_connection.scalar(
                    select(func.count()).select_from(table)
                )
                if count:
                    populated.append(f"{table.name}={count}")
            if populated:
                raise SystemExit(
                    "Target database is not empty; migration stopped: "
                    + ", ".join(populated)
                )

        with source_engine.connect() as source_connection:
            with target_engine.begin() as target_connection:
                for target_table in db.metadata.sorted_tables:
                    source_table = source_metadata.tables.get(target_table.name)
                    if source_table is None:
                        copied[target_table.name] = 0
                        continue
                    common_columns = [
                        column.name
                        for column in target_table.columns
                        if column.name in source_table.c
                    ]
                    rows = source_connection.execute(
                        select(*[source_table.c[name] for name in common_columns])
                    ).mappings()
                    batch = []
                    count = 0
                    for row in rows:
                        batch.append(
                            converted_row(row, target_table, common_columns)
                        )
                        if len(batch) == 500:
                            target_connection.execute(target_table.insert(), batch)
                            count += len(batch)
                            batch = []
                    if batch:
                        target_connection.execute(target_table.insert(), batch)
                        count += len(batch)
                    copied[target_table.name] = count

                preparer = target_engine.dialect.identifier_preparer
                for table in db.metadata.sorted_tables:
                    if "id" not in table.c or not table.c.id.primary_key:
                        continue
                    quoted_table = preparer.quote(table.name)
                    target_connection.execute(
                        text(
                            "SELECT setval("
                            "pg_get_serial_sequence(:relation, 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM {quoted_table}), 1), "
                            f"EXISTS(SELECT 1 FROM {quoted_table})"
                            ")"
                        ),
                        {"relation": quoted_table},
                    )

    print("Migration completed")
    for table_name, count in copied.items():
        if count:
            print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
