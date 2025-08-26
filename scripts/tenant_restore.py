#!/usr/bin/env python3
"""Restore a tenant database from a backup file."""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

# Allow importing application modules when executed directly
sys.path.append(str(Path(__file__).resolve().parents[1]))
from api.app.db.tenant import build_dsn  # type: ignore


def _sqlite_path(dsn: str) -> Path:
    """Return the SQLite file path from a DSN."""

    return Path(dsn.split("///", 1)[1])


def _ensure_database(tenant: str) -> None:
    """Ensure the tenant database or schema exists."""

    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("tenant_create_db.py")),
            "--tenant",
            tenant,
        ],
        check=True,
    )


def _decrypt_backup(backup_file: Path) -> Path:
    """Decrypt ``backup_file`` using ``age`` and return the plaintext path."""

    key = os.environ.get("BACKUP_PRIVATE_KEY")
    if not key:
        raise RuntimeError("BACKUP_PRIVATE_KEY is required for encrypted restores")

    with tempfile.NamedTemporaryFile("w", delete=False) as key_fh:
        key_fh.write(key)
        key_path = key_fh.name

    fd, tmp_path = tempfile.mkstemp()
    os.close(fd)
    try:
        subprocess.run(
            ["age", "--decrypt", "-i", key_path, "-o", tmp_path, str(backup_file)],
            check=True,
        )
    finally:
        os.unlink(key_path)

    return Path(tmp_path)


def restore(tenant: str, backup_file: Path) -> None:
    """Restore ``tenant`` from ``backup_file``."""

    _ensure_database(tenant)
    dsn = build_dsn(tenant)
    backend = dsn.split(":", 1)[0]

    tmp_decrypted: Path | None = None
    if backup_file.suffix == ".age":
        tmp_decrypted = _decrypt_backup(backup_file)
        backup_file = tmp_decrypted

    try:
        if backend.startswith("sqlite"):
            db_path = _sqlite_path(dsn)
            if backup_file.suffix == ".sql":
                conn = sqlite3.connect(str(db_path))
                try:
                    with backup_file.open("r", encoding="utf-8") as fh:
                        conn.executescript(fh.read())
                finally:
                    conn.close()
            else:
                shutil.copyfile(backup_file, db_path)
        else:
            if backup_file.suffix == ".sql":
                tool = shutil.which("psql")
                if not tool:
                    raise RuntimeError("psql not available – required for .sql restores")
                subprocess.run([tool, dsn, "-f", str(backup_file)], check=True)
            else:
                tool = shutil.which("pg_restore")
                if not tool:
                    raise RuntimeError("pg_restore not available")
                subprocess.run([tool, "-d", dsn, str(backup_file)], check=True)
    finally:
        if tmp_decrypted and tmp_decrypted.exists():
            tmp_decrypted.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore tenant database from backup")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--file", required=True, type=Path, help="Backup file to restore")
    args = parser.parse_args()
    restore(args.tenant, args.file)


if __name__ == "__main__":
    main()
