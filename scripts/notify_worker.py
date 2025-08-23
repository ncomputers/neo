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
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.models_master import (  # type: ignore  # noqa: E402
    NotificationDLQ,
    NotificationOutbox,
    NotificationRule,
)


def _deliver(rule: NotificationRule, payload: dict) -> None:
    """Send a notification according to its rule."""
    if rule.channel in {"console", "whatsapp_stub", "sms_stub"}:
        print(json.dumps(payload))
    elif rule.channel == "webhook":
        url = (rule.config or {}).get("url")
        if not url:
            raise ValueError("webhook rule missing url")
        requests.post(url, json=payload, timeout=5).raise_for_status()
    else:
        raise ValueError(f"unsupported channel {rule.channel}")


BACKOFF = [60, 300, 1800]  # 1m, 5m, 30m


def _next_attempt(attempts: int) -> datetime:
    delay = BACKOFF[min(attempts - 1, len(BACKOFF) - 1)]
    return datetime.now(timezone.utc) + timedelta(seconds=delay)


def process_once(engine) -> None:
    """Attempt to deliver all queued notifications once."""
    max_attempts = int(os.getenv("OUTBOX_MAX_ATTEMPTS", "5"))
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        events = session.scalars(
            select(NotificationOutbox)
            .where(NotificationOutbox.status == "queued")
            .where(
                (NotificationOutbox.next_attempt_at == None)
                | (NotificationOutbox.next_attempt_at <= now)
            )
            .order_by(NotificationOutbox.created_at)
        ).all()
        for event in events:
            rule = session.get(NotificationRule, event.rule_id)
            if rule is None:
                event.status = "delivered"
                session.add(event)
                continue
            try:
                _deliver(rule, event.payload)
            except Exception as exc:
                event.attempts += 1
                if event.attempts > max_attempts:
                    session.add(
                        NotificationDLQ(
                            original_id=event.id,
                            rule_id=event.rule_id,
                            payload=event.payload,
                            error=str(exc),
                        )
                    )
                    session.delete(event)
                else:
                    event.next_attempt_at = _next_attempt(event.attempts)
                    session.add(event)
                continue
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
