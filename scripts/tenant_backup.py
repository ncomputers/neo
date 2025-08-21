#!/usr/bin/env python3
# tenant_backup.py
"""Export a tenant database to a backup file."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from api.app.db.tenant import build_dsn


def _sqlite_path(dsn: str) -> Path:
    """Return the SQLite file path from a DSN."""

    return Path(dsn.split("///", 1)[1])


def _export_sqlite(db_path: Path, out_path: Path) -> None:
    """Export a SQLite database to ``out_path``."""

    if out_path.suffix == ".sql":
        conn = sqlite3.connect(str(db_path))
        try:
            with out_path.open("w", encoding="utf-8") as fh:
                for line in conn.iterdump():
                    fh.write(f"{line}\n")
        finally:
            conn.close()
    else:
        shutil.copyfile(db_path, out_path)


def _export_json_sqlite(db_path: Path, out_path: Path) -> None:
    """Write a JSON dump of all tables in the SQLite database."""

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        tables = [
            r[0]
            for r in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        ]
        payload = {}
        for table in tables:
            rows = cursor.execute(f"SELECT * FROM {table}").fetchall()
            cols = [c[0] for c in cursor.description]
            payload[table] = [dict(zip(cols, row)) for row in rows]
    finally:
        conn.close()
    out_path.write_text(json.dumps(payload))


def backup(tenant: str, out_path: Path) -> None:
    """Perform the backup for ``tenant`` to ``out_path``."""

    dsn = build_dsn(tenant)
    backend = dsn.split(":", 1)[0]
    if backend.startswith("sqlite"):
        db_path = _sqlite_path(dsn)
        if out_path.suffix == ".json":
            _export_json_sqlite(db_path, out_path)
        else:
            _export_sqlite(db_path, out_path)
    else:
        if out_path.suffix == ".json":
            out_path.write_text(json.dumps({"todo": "implement postgres export"}))
        else:
            pg_dump = shutil.which("pg_dump")
            if not pg_dump:
                raise RuntimeError("pg_dump not available – TODO: invoke pg_dump for backups")
            subprocess.run([pg_dump, dsn, "-f", str(out_path)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tenant backup utility")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--out", required=True, type=Path, help="Output file path")
    args = parser.parse_args()
    backup(args.tenant, args.out)


if __name__ == "__main__":
    main()
