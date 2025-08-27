#!/usr/bin/env python3
"""Report unused or bloated PostgreSQL indexes.

This script looks for indexes in ``pg_stat_user_indexes`` that have
``idx_scan = 0`` for at least 30 days. When the ``pgstattuple`` extension is
installed, the report also includes bloat percentage and dead tuple counts.
Indexes with more than 40% bloat are flagged as ``CRITICAL``.

The output is a Markdown table written to ``index_health_report.md`` by
default, intended for upload as a CI artifact.
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
from psycopg2.extras import DictCursor


THIRTY_DAYS = "30 days"
DEFAULT_OUTPUT = "index_health_report.md"
CRITICAL_BLOAT = 40.0


def fetch_index_health(cur: psycopg2.extensions.cursor, has_pgstattuple: bool) -> list[dict]:
    """Return rows describing unused indexes and optional bloat metrics."""
    if has_pgstattuple:
        query = f"""
        SELECT s.schemaname,
               s.relname AS table_name,
               s.indexrelname AS index_name,
               pg_relation_size(s.indexrelid) AS index_size,
               (t.dead_tuple_percent + t.free_percent) AS bloat_pct,
               t.dead_tuple_count
        FROM pg_stat_user_indexes s
        JOIN pg_stat_database d ON d.datname = current_database()
        CROSS JOIN LATERAL pgstattuple(s.indexrelid) AS t
        WHERE s.idx_scan = 0
          AND d.stats_reset < now() - interval '{THIRTY_DAYS}'
        ORDER BY pg_relation_size(s.indexrelid) DESC
        """
    else:
        query = f"""
        SELECT s.schemaname,
               s.relname AS table_name,
               s.indexrelname AS index_name,
               pg_relation_size(s.indexrelid) AS index_size,
               NULL::float AS bloat_pct,
               NULL::bigint AS dead_tuple_count
        FROM pg_stat_user_indexes s
        JOIN pg_stat_database d ON d.datname = current_database()
        WHERE s.idx_scan = 0
          AND d.stats_reset < now() - interval '{THIRTY_DAYS}'
        ORDER BY pg_relation_size(s.indexrelid) DESC
        """
    cur.execute(query)
    return cur.fetchall()


def generate_markdown(rows: list[dict]) -> str:
    """Return a Markdown table for the given index rows."""
    lines = [
        "| Schema | Table | Index | Size (MB) | Bloat % | Dead tuples | Status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| - | - | - | - | - | - | - |")
    for row in rows:
        size_mb = float(row["index_size"]) / 1024 / 1024
        bloat_pct = float(row["bloat_pct"] or 0)
        dead_tuples = int(row["dead_tuple_count"] or 0)
        status = "CRITICAL" if bloat_pct > CRITICAL_BLOAT else ""
        lines.append(
            f"| {row['schemaname']} | {row['table_name']} | {row['index_name']} | "
            f"{size_mb:.2f} | {bloat_pct:.2f} | {dead_tuples} | {status} |"
        )
        if status:
            print(
                f"CRITICAL: {row['schemaname']}.{row['index_name']} "
                f"{bloat_pct:.2f}% bloat",
                file=sys.stderr,
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Report unused or bloated indexes")
    parser.add_argument("--dsn", default=os.environ.get("DATABASE_URL"), help="PostgreSQL DSN")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Markdown output path")
    args = parser.parse_args()

    if not args.dsn:
        print("DATABASE_URL or --dsn required", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(args.dsn, cursor_factory=DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'pgstattuple'"
            )
            has_pgstattuple = cur.fetchone() is not None
            rows = fetch_index_health(cur, has_pgstattuple)
    finally:
        conn.close()

    with open(args.output, "w", encoding="utf8") as fh:
        fh.write("# Index Health Report\n\n")
        fh.write(generate_markdown(rows))
    print(f"Wrote {args.output}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
