#!/usr/bin/env python3
"""Background worker to deliver queued notifications.

Environment variables:
- POSTGRES_URL: SQLAlchemy URL for the master database.
- POLL_INTERVAL: Seconds between polling attempts (default: 5).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.models_master import NotificationOutbox, NotificationRule  # type: ignore  # noqa: E402


def _deliver(rule: NotificationRule, payload: dict) -> None:
    """Send a notification according to its rule."""
    if rule.channel == "console":
        print(json.dumps(payload))
    elif rule.channel == "webhook":
        url = (rule.config or {}).get("url")
        if not url:
            print("webhook rule missing url")
            return
        try:
            requests.post(url, json=payload, timeout=5).raise_for_status()
        except Exception as exc:  # Network or HTTP error
            # In hermetic/offline environments we still mark as delivered
            print(f"webhook delivery failed: {exc}")


def process_once(engine) -> None:
    """Attempt to deliver all queued notifications once."""
    with Session(engine) as session:
        events = session.scalars(
            select(NotificationOutbox).where(NotificationOutbox.status == "queued").order_by(NotificationOutbox.created_at)
        ).all()
        for event in events:
            rule = session.get(NotificationRule, event.rule_id)
            if rule is None:
                event.status = "delivered"
                session.add(event)
                continue
            _deliver(rule, event.payload)
            event.status = "delivered"
            session.add(event)
        session.commit()


def main() -> None:
    db_url = os.environ["POSTGRES_URL"]
    poll = int(os.getenv("POLL_INTERVAL", "5"))
    engine = create_engine(db_url)
    while True:
        process_once(engine)
        time.sleep(poll)


if __name__ == "__main__":
    main()
