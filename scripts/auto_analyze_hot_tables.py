#!/usr/bin/env python3
"""Refresh planner stats for hot tables after bulk imports."""

from __future__ import annotations

from sqlalchemy import text

from api.app.db import SessionLocal

TABLES = [
    "orders",
    "order_items",
    "payments",
    "menu_items",
    "audit_log",
    "webhook_events",
]

THRESHOLD = 1.2  # 20% growth


def analyze_hot_tables() -> None:
    """Run ``ANALYZE`` for tables that grew beyond ``THRESHOLD`` since last analyze."""
    with SessionLocal() as session:
        for table in TABLES:
            res = session.execute(
                text(
                    "SELECT c.reltuples, s.n_live_tup "
                    "FROM pg_class c "
                    "JOIN pg_stat_user_tables s ON s.relid = c.oid "
                    "WHERE c.relname = :table"
                ),
                {"table": table},
            ).one_or_none()
            if not res:
                continue
            reltuples, n_live_tup = res
            if reltuples == 0 or n_live_tup > reltuples * THRESHOLD:
                session.execute(text(f"ANALYZE {table}"))  # nosec B608
                print(f"ANALYZE {table}")
        session.commit()


if __name__ == "__main__":  # pragma: no cover - manual invocation
    analyze_hot_tables()
