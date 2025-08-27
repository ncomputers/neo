#!/usr/bin/env python3
"""Purge tenant data according to a retention window."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.services import retention  # type: ignore  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge tenant data")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--days", type=int, required=True, help="Retention window in days")
    args = parser.parse_args()
    asyncio.run(retention.apply(args.tenant, args.days))


if __name__ == "__main__":
    main()
