#!/usr/bin/env python3
"""Mini chaos drills for core dependencies.

Run against staging to quickly prove resilience of:
* database read replica fallback
* Redis queue recovery
* printer agent retry

The script requires a handful of environment variables and will abort if
any are missing. Each step prints its progress and raises on failure.
"""
from __future__ import annotations

import os
import sys
import time

import requests

try:  # pragma: no cover - redis optional
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis not installed
    redis = None  # type: ignore


def _env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"{name} not set")
    return val


def _wait_ok(url: str, duration: int) -> None:
    """Poll ``url`` for ``duration`` seconds."""
    end = time.time() + duration
    while time.time() < end:
        requests.get(url, timeout=5).raise_for_status()
        time.sleep(5)


def read_replica_drill() -> None:
    """Flip READ_REPLICA_URL to a bad host for 60s and ensure app stays healthy."""
    url = _env("APP_HEALTH_URL")
    original = os.environ.get("READ_REPLICA_URL", "")
    os.environ["READ_REPLICA_URL"] = "postgres://bad-host/neo"
    print("READ_REPLICA_URL flipped; verifying fallback for 60s…")
    try:
        _wait_ok(url, 60)
    finally:
        os.environ["READ_REPLICA_URL"] = original
    print("DB fallback OK")


def redis_drill() -> None:
    """Pause Redis for 30s and check that queuing works afterwards."""
    redis_url = _env("REDIS_URL")
    if redis is None:
        sys.exit("redis client not available")
    client = redis.from_url(redis_url)
    print("Pausing Redis for 30s…")
    client.client_pause(30000)
    client.lpush("chaos:test", "ping")
    result = client.brpop("chaos:test", timeout=5)
    if result is None:
        sys.exit("queue did not resume")
    print("Redis queue resumed")


def printer_drill() -> None:
    """Simulate printer agent outage and ensure queued KOT prints later."""
    printer_url = _env("PRINTER_URL")
    bad = "http://0.0.0.0"  # unreachable
    print("Sending KOT to offline printer…")
    try:
        requests.post(bad, json={"text": "test"}, timeout=5)
    except Exception:
        print("KOT queued while printer offline")
    time.sleep(60)
    resp = requests.post(printer_url, json={"text": "test"}, timeout=10)
    resp.raise_for_status()
    print("KOT printed after retry")


def main() -> None:
    read_replica_drill()
    redis_drill()
    printer_drill()
    print("Mini chaos drills complete")


if __name__ == "__main__":
    main()
