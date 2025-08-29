#!/usr/bin/env python3
"""Ping health endpoints and record incidents in a sqlite DB."""
from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

import requests

URLS = {
    "api": "/status.json",
    "deps": "/status/deps",
}


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
    conn.close()


if __name__ == "__main__":
    main()
