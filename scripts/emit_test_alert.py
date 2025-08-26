#!/usr/bin/env python3
"""Push a synthetic alert to Alertmanager.

Usage:
    python scripts/emit_test_alert.py --message "Test alert"

Environment variables:
- ALERTMANAGER_URL: Base URL for Alertmanager (e.g. http://localhost:9093)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a sample alert to Alertmanager")
    parser.add_argument(
        "--message", default="Test alert from runbook", help="Summary text"
    )
    args = parser.parse_args()

    url = os.environ.get("ALERTMANAGER_URL")
    if not url:
        sys.exit("ALERTMANAGER_URL not set")

    payload = [
        {
            "labels": {"alertname": "SyntheticTestAlert", "severity": "info"},
            "annotations": {"summary": args.message},
            "startsAt": dt.datetime.utcnow().isoformat() + "Z",
        }
    ]

    resp = requests.post(f"{url}/api/v1/alerts", json=payload, timeout=5)
    resp.raise_for_status()
    print("Alert dispatched")


if __name__ == "__main__":
    main()
