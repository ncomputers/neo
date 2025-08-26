#!/usr/bin/env python3
"""Aggregate daily NPS feedback per outlet and send a summary."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
import sys

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from api.app.routes_feedback import FEEDBACK_STORE  # type: ignore


class ConsoleEmail:
    """Simple provider that prints an email to STDOUT."""

    @staticmethod
    def send(subject: str, body: str) -> None:
        print(subject)
        if body:
            print(body)


EMAIL_PROVIDER = ConsoleEmail()


def aggregate(day: date) -> dict[str, float]:
    """Return NPS score per tenant for ``day``."""

    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)
    result: dict[str, float] = {}
    for tenant, records in FEEDBACK_STORE.items():
        day_records = [r for r in records if start <= r.timestamp <= end]
        total = len(day_records)
        if not total:
            continue
        promoters = sum(1 for r in day_records if r.score >= 9)
        detractors = sum(1 for r in day_records if r.score <= 6)
        result[tenant] = (promoters - detractors) / total * 100
    return result


def main(date_str: str | None = None) -> dict[str, float]:
    """Aggregate NPS for the previous day and send summary via email."""

    day = (
        date.today() - timedelta(days=1)
        if date_str is None
        else datetime.strptime(date_str, "%Y-%m-%d").date()
    )
    summary = aggregate(day)
    lines = [f"{tenant}: {score:.1f}" for tenant, score in summary.items()]
    EMAIL_PROVIDER.send("Daily NPS Summary", "\n".join(lines))
    return summary


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()

