#!/usr/bin/env python3
"""Aggregate pilot NPS feedback and email a daily summary."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, Iterable

# Ensure api package importable
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from api.app.providers import email_stub  # type: ignore  # noqa: E402
from api.app.routes_pilot_feedback import (  # type: ignore  # noqa: E402
    PILOT_FEEDBACK_STORE,
    PilotFeedbackRecord,
)


def _compute_nps(records: Iterable[PilotFeedbackRecord]) -> float:
    records = list(records)
    promoters = sum(1 for r in records if r.score >= 9)
    detractors = sum(1 for r in records if r.score <= 6)
    total = len(records)
    if total == 0:
        return 0.0
    return (promoters - detractors) / total * 100.0


def aggregate(day: date) -> Dict[str, dict]:
    """Return NPS and count per tenant for ``day``."""

    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)
    result: Dict[str, dict] = {}
    for tenant, records in PILOT_FEEDBACK_STORE.items():
        day_records = [r for r in records if start <= r.timestamp <= end]
        if not day_records:
            continue
        result[tenant] = {
            "nps": _compute_nps(day_records),
            "count": len(day_records),
        }
    return result


def build_digest(day: date | None = None) -> str:
    day = day or datetime.utcnow().date()
    summary = aggregate(day)
    lines = [f"Pilot NPS digest {day.isoformat()}"]
    for tenant, stats in summary.items():
        lines.append(f"{tenant}: nps={stats['nps']:.1f} count={stats['count']}")
    message = "\n".join(lines)
    subject = f"Pilot NPS digest {day.isoformat()}"
    email_target = os.getenv("PILOT_NPS_EMAIL")
    if email_target:
        email_stub.send(
            "pilot.nps", {"subject": subject, "message": message}, email_target
        )
    return message


def main() -> str:
    return build_digest()


if __name__ == "__main__":
    main()
