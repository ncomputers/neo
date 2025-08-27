#!/usr/bin/env python3
"""Detach and drop old ``audit_log`` partitions."""

from __future__ import annotations

import argparse
import re
from datetime import datetime

from sqlalchemy import text

from api.app.db import SessionLocal

PARTITION_RE = re.compile(r"audit_log_y(\d{4})m(\d{2})")


def drop_old_partitions(keep_months: int = 6) -> None:
    """Remove ``audit_log`` partitions older than ``keep_months`` months."""

    now = datetime.utcnow().replace(day=1)
    year, month = now.year, now.month - keep_months
    while month <= 0:
        month += 12
        year -= 1
    keep_from = datetime(year, month, 1)

    with SessionLocal() as session:
        res = session.execute(
            text(
                "SELECT inhrelid::regclass::text FROM pg_inherits "
                "JOIN pg_class parent ON parent.oid = inhparent "
                "WHERE parent.relname = 'audit_log'"
            )
        )
        for (name,) in res:
            match = PARTITION_RE.match(name)
            if not match:
                continue
            part_date = datetime(int(match.group(1)), int(match.group(2)), 1)
            if part_date < keep_from:
                session.execute(
                    text(f"ALTER TABLE audit_log DETACH PARTITION {name}")
                )  # nosec B608
                session.execute(text(f"DROP TABLE IF EXISTS {name}"))  # nosec B608
        session.commit()


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Drop old audit_log partitions")
    parser.add_argument(
        "--keep-months",
        type=int,
        default=6,
        help="How many months of partitions to keep (default: 6)",
    )
    args = parser.parse_args()
    drop_old_partitions(args.keep_months)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    _cli()
