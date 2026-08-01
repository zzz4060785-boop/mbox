"""Create and retain PostgreSQL backups for the Friendary production DB."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.engine import make_url


BACKUP_DIR = Path(os.getenv("DB_BACKUP_DIR", "/opt/friendary/db-backups"))
RETENTION_DAYS = max(1, int(os.getenv("DB_BACKUP_RETENTION_DAYS", "30")))


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    url = make_url(database_url)
    if not url.database or not url.username:
        raise RuntimeError("DATABASE_URL is missing a database or user")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    final_path = BACKUP_DIR / f"friendary-{timestamp}.dump"
    temporary_path = final_path.with_suffix(".dump.tmp")

    environment = os.environ.copy()
    environment["PGPASSWORD"] = url.password or ""

    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--host",
        url.host or "127.0.0.1",
        "--port",
        str(url.port or 5432),
        "--username",
        url.username,
        "--file",
        str(temporary_path),
        url.database,
    ]

    try:
        subprocess.run(command, check=True, env=environment)
        if not temporary_path.exists() or temporary_path.stat().st_size == 0:
            raise RuntimeError("pg_dump created an empty backup")
        temporary_path.replace(final_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    for backup_path in BACKUP_DIR.glob("friendary-*.dump"):
        modified_at = datetime.fromtimestamp(
            backup_path.stat().st_mtime,
            tz=timezone.utc,
        )
        if modified_at < cutoff:
            backup_path.unlink()

    print(final_path)


if __name__ == "__main__":
    main()
