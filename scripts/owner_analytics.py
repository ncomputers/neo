#!/usr/bin/env python3
"""CLI for computing owner activation and retention metrics."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.services.owner_analytics import compute_owner_time_series  # noqa: E402


async def _run(days: int) -> None:
    data = await compute_owner_time_series(days)
    print(json.dumps(data, indent=2))


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Compute owner activation/retention metrics",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to include",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.days))


if __name__ == "__main__":
    _cli()
