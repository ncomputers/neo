#!/usr/bin/env python3
"""Ping health endpoints and record incidents in a sqlite DB."""
from __future__ import annotations

import argparse
import sqlite3
import time
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

URLS = {
    "api": "/status.json",
    "deps": "/status/deps",
}

FEED_FILE = Path(__file__).resolve().parent.parent / "incidents.json"
INTERVAL_SECS = 60  # expected probe frequency


def main() -> None:
    parser = argparse.ArgumentParser(description="Uptime probe")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--db", default="incidents.db")
    args = parser.parse_args()

    db_path = Path(args.db)
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS incidents(service TEXT, ts REAL)")

    for service, path in URLS.items():
        ok = True
        try:
            resp = requests.get(args.base_url + path, timeout=5)
            resp.raise_for_status()
        except Exception:
            ok = False
        if not ok:
            conn.execute(
                "INSERT INTO incidents(service, ts) VALUES (?, ?)",
                (service, time.time()),
            )
            conn.commit()

    now = time.time()
    summary = {}
    for days, key in [(7, "7d"), (30, "30d")]:
        since = now - days * 86400
        rows = conn.execute(
            "SELECT service, ts FROM incidents WHERE ts >= ? ORDER BY ts DESC",
            (since,),
        ).fetchall()
        summary[f"incidents_{key}"] = [
            {
                "service": service,
                "ts": datetime.fromtimestamp(ts, timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
            for service, ts in rows
        ]
        total_checks = days * 86400 / INTERVAL_SECS * len(URLS)
        uptime = 1 - len(rows) / total_checks
        summary[f"uptime_{key}"] = round(uptime * 100, 2)

    with FEED_FILE.open("w") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    conn.close()


if __name__ == "__main__":
    main()
