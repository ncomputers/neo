#!/usr/bin/env python3
"""Disaster recovery restore drill.

Restores the latest backup into a temporary SQLite database and runs a
set of smoke checks against both the production database and the
restored copy. The script exits with a non-zero status if any of the
checks fail or if counts differ, making it suitable for automated
runs.
"""
from __future__ import annotations

import argparse
import glob
import shutil
import sqlite3
import sys
import time
from pathlib import Path


def restore_latest(pattern: str, tmp_db: Path) -> float:
    """Restore the newest backup matching ``pattern`` into ``tmp_db``.

    Returns the time taken to restore in seconds.
    """
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise RuntimeError("no matching backups")
    backup = Path(matches[-1])

    if tmp_db.exists():
        tmp_db.unlink()

    start = time.time()
    if backup.suffix == ".sql":
        conn = sqlite3.connect(tmp_db)
        try:
            with backup.open("r", encoding="utf-8") as fh:
                conn.executescript(fh.read())
        finally:
            conn.close()
    else:
        shutil.copyfile(backup, tmp_db)
    return time.time() - start


def compare_counts(prod_db: Path, tmp_db: Path, tables: list[str]) -> bool:
    """Return ``True`` if row counts match for all ``tables``."""
    prod = sqlite3.connect(prod_db)
    tmp = sqlite3.connect(tmp_db)
    ok = True
    try:
        for table in tables:
            prod_cnt = prod.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            tmp_cnt = tmp.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if prod_cnt != tmp_cnt:
                print(
                    f"FAIL: {table} count mismatch (prod={prod_cnt} restored={tmp_cnt})"
                )
                ok = False
    finally:
        prod.close()
        tmp.close()
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="DR restore drill")
    parser.add_argument("--file", required=True, help="Glob pattern for backups")
    parser.add_argument("--prod-db", required=True, type=Path, help="Live SQLite DB")
    parser.add_argument(
        "--tmp-db",
        required=True,
        type=Path,
        help="Path for temporary restored SQLite DB",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        required=True,
        help="Tables to compare using COUNT(*)",
    )
    args = parser.parse_args()

    try:
        restore_time = restore_latest(args.file, args.tmp_db)
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)

    ok = compare_counts(args.prod_db, args.tmp_db, args.tables)
    print(f"RTO: {restore_time:.2f}s")
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
