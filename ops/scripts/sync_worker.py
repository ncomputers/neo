#!/usr/bin/env python3
"""Background worker to push queued events to the cloud API.

Environment variables:
- POSTGRES_URL: SQLAlchemy URL for the tenant database.
- CLOUD_API_URL: Endpoint that receives queued events.
- POLL_INTERVAL: Seconds between polling attempts (default: 5).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR / "api"))

from app.models_master import SyncOutbox  # type: ignore  # noqa: E402


def process_once(engine, api_url: str) -> None:
    """Attempt to send all queued events once."""
    with Session(engine) as session:
        events = session.scalars(
            select(SyncOutbox).order_by(SyncOutbox.created_at)
        ).all()
        for event in events:
            try:
                resp = requests.post(
                    api_url,
                    json={"type": event.event_type, "payload": event.payload},
                    timeout=5,
                )
                resp.raise_for_status()
            except Exception as exc:  # Network or HTTP error
                event.retries += 1
                event.last_error = str(exc)
                session.add(event)
            else:
                session.delete(event)
            session.commit()


def main() -> None:
    db_url = os.environ["POSTGRES_URL"]
    api_url = os.environ["CLOUD_API_URL"]
    poll = int(os.getenv("POLL_INTERVAL", "5"))
    engine = create_engine(db_url)
    while True:
        process_once(engine, api_url)
        time.sleep(poll)


if __name__ == "__main__":
    main()
