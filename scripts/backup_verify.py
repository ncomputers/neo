#!/usr/bin/env python3
"""Verify that backups can be restored successfully.

Given a glob pattern for backup SQL files, the latest matching dump is loaded
into a temporary SQLite database. A couple of sanity checks are executed and the
script prints ``PASS`` or ``FAIL`` and exits with an appropriate status code.
"""

from __future__ import annotations

import argparse
import glob
import sqlite3
import sys
from pathlib import Path


def verify(pattern: str, tmp_db: Path) -> bool:
    """Return ``True`` if the latest dump matching ``pattern`` restores cleanly."""

    matches = sorted(glob.glob(pattern))
    if not matches:
        print("FAIL: no matching backups")
        return False
    backup = Path(matches[-1])

    if tmp_db.exists():
        tmp_db.unlink()

    try:
        conn = sqlite3.connect(tmp_db)
        try:
            with backup.open("r", encoding="utf-8") as fh:
                conn.executescript(fh.read())
            cur = conn.cursor()
            checks = [
                ("PRAGMA integrity_check", lambda rows: rows[0][0] == "ok"),
                (
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'",
                    lambda rows: rows[0][0] > 0,
                ),
            ]
            for sql, validator in checks:
                rows = cur.execute(sql).fetchall()
                if not validator(rows):
                    print(f"FAIL: {sql}")
                    return False
        finally:
            conn.close()
    except sqlite3.Error as exc:
        print(f"FAIL: {exc}")
        return False
    finally:
        if tmp_db.exists():
            tmp_db.unlink()

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify backup restore")
    parser.add_argument(
        "--file",
        required=True,
        help="Glob pattern for backup files (e.g. /backups/TENANT-*.sql)",
    )
    parser.add_argument(
        "--sqlite-tmp",
        required=True,
        type=Path,
        help="Temporary SQLite database path",
    )
    args = parser.parse_args()

    ok = verify(args.file, args.sqlite_tmp)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
