#!/usr/bin/env python3
"""Emit a test alert via the configured webhook.

Usage:
    python scripts/emit_test_alert.py --message "Test alert"

Environment variables:
- ALERT_WEBHOOK_URL: Destination webhook URL to post the alert.
"""

from __future__ import annotations

import argparse
import os
import sys

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a test alert")
    parser.add_argument(
        "--message", default="Test alert from runbook", help="Message text"
    )
    args = parser.parse_args()

    url = os.environ.get("ALERT_WEBHOOK_URL")
    if not url:
        sys.exit("ALERT_WEBHOOK_URL not set")

    resp = requests.post(url, json={"text": args.message}, timeout=5)
    resp.raise_for_status()
    print("Alert dispatched")


if __name__ == "__main__":
    main()
