#!/usr/bin/env python3
"""Aggregate pilot NPS feedback and email a daily summary."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import sys
from typing import Iterable

# Ensure api package importable
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from api.app.routes_pilot_feedback import (  # type: ignore  # noqa: E402
    PILOT_FEEDBACK_STORE,
    PilotFeedbackRecord,
)
from api.app.providers import email_stub  # type: ignore  # noqa: E402


def _compute_nps(records: Iterable[PilotFeedbackRecord]) -> float:
    promoters = sum(1 for r in records if r.score >= 9)
    detractors = sum(1 for r in records if r.score <= 6)
    total = len(list(records))
    if total == 0:
        return 0.0
    return (promoters - detractors) / total * 100.0


def build_digest() -> str:
    today = datetime.utcnow().date().isoformat()
    lines = [f"Pilot NPS digest {today}"]
    for tenant, records in PILOT_FEEDBACK_STORE.items():
        nps = _compute_nps(records)
        lines.append(f"{tenant}: nps={nps:.1f} count={len(records)}")
    message = "\n".join(lines)
    subject = f"Pilot NPS digest {today}"
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
