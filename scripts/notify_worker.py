#!/usr/bin/env python3
"""Background worker to deliver queued notifications.

Environment variables:
- POSTGRES_URL: SQLAlchemy URL for the master database.
- POLL_INTERVAL: Seconds between polling attempts (default: 5).
- OUTBOX_MAX_ATTEMPTS: Max delivery attempts before DLQ (default: 5).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
import hashlib
import hmac
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


PROVIDER_REGISTRY = {
    "whatsapp": os.getenv("ALERTS_WHATSAPP_PROVIDER", "app.providers.whatsapp_stub"),
    "sms": os.getenv("ALERTS_SMS_PROVIDER", "app.providers.sms_stub"),
}


try:  # Optional Redis client for replay protection
    import redis  # type: ignore
    from redis.exceptions import RedisError  # type: ignore
except Exception:  # pragma: no cover - redis not installed
    redis = None  # type: ignore
    RedisError = Exception  # type: ignore

REDIS_CLIENT = None
if redis is not None:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            REDIS_CLIENT = redis.from_url(redis_url)
        except Exception:  # pragma: no cover - connection issues
            REDIS_CLIENT = None


def sign_webhook(body: str, secret: str, timestamp: str | None = None) -> tuple[str, str]:
    """Return timestamp and signature header for a webhook body."""
    ts = timestamp or str(int(time.time()))
    digest = hmac.new(
        secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return ts, f"sha256={digest}"


def _deliver(rule: NotificationRule, event: NotificationOutbox) -> None:
    """Send a notification according to its rule."""
    payload = event.payload
    target = (rule.config or {}).get("target")
    if rule.channel == "console":
        print(json.dumps(payload))
    elif rule.channel == "webhook":
        url = (rule.config or {}).get("url")
        if not url:
            raise ValueError("webhook rule missing url")
        secret = os.getenv("WEBHOOK_SIGNING_SECRET")
        body = json.dumps(payload, separators=(",", ":"))
        headers = {"Content-Type": "application/json"}
        if secret:
            ts, sig = sign_webhook(body, secret)
            headers["X-Webhook-Timestamp"] = ts
            headers["X-Webhook-Signature"] = sig
            nonce = f"{ts}.{sig.split('=', 1)[1]}"
            if REDIS_CLIENT is not None:
                try:
                    REDIS_CLIENT.setex(nonce, 300, "1")
                except RedisError:  # pragma: no cover - redis failure
                    pass
        requests.post(url, data=body, headers=headers, timeout=5).raise_for_status()
    elif rule.channel in PROVIDER_REGISTRY:
        module = importlib.import_module(PROVIDER_REGISTRY[rule.channel])
        module.send(event, payload, target)
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
                _deliver(rule, event)
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
