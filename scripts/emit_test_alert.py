#!/usr/bin/env python3
"""Push a synthetic alert to Alertmanager to verify paging.

Usage:
    python scripts/emit_test_alert.py --message "Test alert"

Environment variables:
- ALERTMANAGER_URL: Base URL for Alertmanager (e.g. http://localhost:9093)
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a sample alert")
    parser.add_argument(
        "--message", default="Test alert from runbook", help="Summary text"
    )
    args = parser.parse_args()

    url = os.environ.get("ALERTMANAGER_URL")
    if url:
        try:
            ping = requests.get(url, timeout=5)
            ping.raise_for_status()
        except Exception as exc:
            raise SystemExit(f"Alertmanager unreachable at {url}: {exc}") from exc

        payload = [
            {
                "labels": {"alertname": "SyntheticTestAlert", "severity": "critical"},
                "annotations": {"summary": args.message},
                "startsAt": dt.datetime.utcnow().isoformat() + "Z",
            }
        ]

        resp = requests.post(f"{url}/api/v1/alerts", json=payload, timeout=5)
        resp.raise_for_status()
        print("Alert dispatched")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("Synthetic alert: %s", args.message)


if __name__ == "__main__":
    main()
