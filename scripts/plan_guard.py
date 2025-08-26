"""Query plan regression guard.

Runs EXPLAIN (ANALYZE, BUFFERS) for hot queries and fails if the p95
execution time regresses beyond an acceptable threshold.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Iterable, List

import psycopg2


def compute_p95(values: Iterable[float]) -> float:
    """Return the 95th percentile from an iterable of numbers."""
    values = sorted(values)
    if not values:
        return 0.0
    index = max(math.ceil(0.95 * len(values)) - 1, 0)
    return values[index]


def guard_query(name: str, durations: List[float], baseline_ms: float) -> float:
    """Validate that the p95 does not exceed the baseline threshold.

    Returns the p95 value and raises ``RuntimeError`` on regression.
    """
    p95_ms = compute_p95(durations)
    if p95_ms > baseline_ms * 1.2:
        raise RuntimeError(
            f"{name} regression: p95 {p95_ms:.2f}ms exceeds "
            f"baseline {baseline_ms:.2f}ms"
        )
    return p95_ms


def run_explain(conn, sql: str, runs: int) -> List[float]:
    """Run EXPLAIN ANALYZE with buffers and collect execution times."""
    durations: List[float] = []
    for _ in range(runs):
        with conn.cursor() as cur:
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
            plan = cur.fetchone()[0][0]
            durations.append(float(plan["Execution Time"]))
    return durations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Guard hot queries against regressions"
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection string",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".ci" / "baselines",
        help="Directory containing query baseline JSON files",
    )
    parser.add_argument(
        "--runs", type=int, default=5, help="Number of executions per query"
    )
    args = parser.parse_args()

    conn = psycopg2.connect(args.dsn)

    failures: List[str] = []
    try:
        for baseline in sorted(args.baseline_dir.glob("*.json")):
            with open(baseline, "r", encoding="utf8") as fh:
                queries = json.load(fh)
            for name, info in queries.items():
                durations = run_explain(conn, info["sql"], args.runs)
                try:
                    p95_ms = guard_query(name, durations, float(info["baseline_ms"]))
                    print(
                        f"{name}: p95 {p95_ms:.2f} ms "
                        f"(baseline {info['baseline_ms']} ms)"
                    )
                except RuntimeError as exc:  # pragma: no cover - exercised in CI
                    failures.append(str(exc))
                    print(str(exc), file=sys.stderr)
    finally:
        conn.close()

    if failures:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
