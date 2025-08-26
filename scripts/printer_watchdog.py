#!/usr/bin/env python3
"""Check printer agent heartbeat and retry queue length."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import redis

HEARTBEAT_KEY = os.getenv("PRINTER_HEARTBEAT_KEY", "print:hb:demo")
QUEUE_KEY = os.getenv("PRINTER_QUEUE_KEY", "print:retry:demo")
STALE_SEC = int(os.getenv("PRINTER_STALE_SEC", "60"))


def main() -> int:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        print("REDIS_URL not set", file=sys.stderr)
        return 1
    r = redis.from_url(redis_url, decode_responses=True)
    last = r.get(HEARTBEAT_KEY)
    queued = r.llen(QUEUE_KEY)
    stale = True
    if last:
        try:
            dt = datetime.fromisoformat(last)
            stale = (datetime.now(timezone.utc) - dt).total_seconds() > STALE_SEC
        except ValueError:
            stale = True
    print(f"queue={queued} stale={stale}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
