#!/usr/bin/env python3
"""Flag stock vs KOT anomalies and alert operations.

Reads a CSV file containing the columns `item`, `sold_qty`, `KOT_cnt` and
`variance`. Entries where the absolute variance exceeds a threshold are
considered anomalous. When anomalies are detected an email is sent to the
operations team.

Environment variables:
- SMTP_HOST: hostname of the SMTP server
- SMTP_PORT: port for the SMTP server (default 25)
- SMTP_USER: optional username for SMTP authentication
- SMTP_PASS: optional password for SMTP authentication
- OPS_EMAIL: destination email address for alerts
- SMTP_FROM: optional override for the From header
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile stock vs KOT and alert on variances"
    )
    parser.add_argument("--csv", required=True, help="Path to input CSV file")
    parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="Variance threshold to flag (default: 5)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


REQUIRED_FIELDS = ["item", "sold_qty", "KOT_cnt", "variance"]


def load_anomalies(path: str, threshold: int) -> List[Dict[str, str]]:
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        anomalies: List[Dict[str, str]] = []
        for row in reader:
            if not all(row.get(f) for f in REQUIRED_FIELDS):
                logging.warning("Skipping row with missing fields: %s", row)
                continue
            try:
                sold_qty = int(row["sold_qty"])
                kot_cnt = int(row["KOT_cnt"])
                variance = int(row["variance"])
            except ValueError:
                logging.warning("Skipping row with non-numeric values: %s", row)
                continue
            if abs(variance) > threshold:
                anomalies.append(
                    {
                        "item": row["item"],
                        "sold_qty": str(sold_qty),
                        "KOT_cnt": str(kot_cnt),
                        "variance": str(variance),
                    }
                )
    return anomalies


def send_email(anomalies: List[Dict[str, str]], threshold: int) -> None:
    host = os.getenv("SMTP_HOST")
    to_addr = os.getenv("OPS_EMAIL")
    if not host or not to_addr:
        logging.warning(
            "Skipping email. Set SMTP_HOST and OPS_EMAIL to enable alerts."
        )
        return

    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM") or user or "noreply@example.com"

    body_lines = [f"Variance greater than {threshold} detected:"]
    for row in anomalies:
        body_lines.append(
            f"{row['item']}: sold {row['sold_qty']}, KOT {row['KOT_cnt']}, variance {row['variance']}"
        )

    msg = EmailMessage()
    msg["Subject"] = "Stock vs KOT reconciliation anomalies"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content("\n".join(body_lines))

    with smtplib.SMTP(host, port) as server:
        if user and password:
            server.starttls()
            server.login(user, password)
        server.send_message(msg)

    logging.info("Alert emailed to %s for %d anomalies", to_addr, len(anomalies))


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    anomalies = load_anomalies(args.csv, args.threshold)
    if anomalies:
        send_email(anomalies, args.threshold)
    else:
        logging.info("No anomalies above threshold")


if __name__ == "__main__":
    main()
