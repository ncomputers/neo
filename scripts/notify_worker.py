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
import random
import sys
import time
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.alerts.render import render_email, render_message  # type: ignore  # noqa: E402
from app.models_master import (  # type: ignore  # noqa: E402
    NotificationDLQ,
    NotificationOutbox,
    NotificationRule,
)
from app.obs import capture_exception, init_sentry  # type: ignore  # noqa: E402
from app.security.webhook_egress import is_allowed_url  # type: ignore  # noqa: E402
from app.utils.webhook_signing import sign  # type: ignore  # noqa: E402

from api.app.routes_metrics import (  # type: ignore  # noqa: E402
    notifications_outbox_delivered_total,
    notifications_outbox_failed_total,
    webhook_attempts_total,
    webhook_failures_total,
    webhook_breaker_state,
)

PROVIDER_REGISTRY = {
    "whatsapp": os.getenv("ALERTS_WHATSAPP_PROVIDER", "app.providers.whatsapp_stub"),
    "sms": os.getenv("ALERTS_SMS_PROVIDER", "app.providers.sms_stub"),
    "email": os.getenv("ALERTS_EMAIL_PROVIDER", "app.providers.email_stub"),
    "webpush": os.getenv("ALERTS_WEBPUSH_PROVIDER", "app.providers.webpush_stub"),
    "slack": os.getenv("ALERTS_SLACK_PROVIDER", "app.providers.slack_stub"),
}

BACKOFF = [1, 5, 30, 120, 600]  # seconds: 1s, 5s, 30s, 2m, 10m

BREAKER_THRESHOLD = int(os.getenv("WEBHOOK_BREAKER_THRESHOLD", "8"))
BREAKER_OPEN_SECS = int(os.getenv("WEBHOOK_BREAKER_OPEN_SECS", "600"))
BREAKERS: dict[str, dict] = {}


def _url_hash(url: str) -> str:
    """Stable hash for metric labels and Redis keys."""
    return hashlib.sha256(url.encode()).hexdigest()[:8]


def _format_sla_breach(channel: str, payload: dict) -> dict:
    items = [b.get("item") for b in payload.get("breaches", [])[:3]]
    vars = {"items": items, "window": payload.get("window", "")}
    if channel == "email":
        return {
            "template": "sla_breach.html",
            "subject": "SLA breach alert",
            "vars": vars,
        }
    if channel == "whatsapp":
        return {"template": "sla_breach.txt", "vars": vars}
    if channel == "slack":
        text = render_message("sla_breach.txt", vars)
        return {"text": text}
    return payload


FORMATTERS = {"sla_breach": _format_sla_breach}


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


def _get_breaker_state(url_hash: str) -> str | None:
    if REDIS_CLIENT is not None:
        state = REDIS_CLIENT.get(f"wh:breaker:{url_hash}")
        return state.decode() if state else None
    breaker = BREAKERS.get(url_hash)
    return breaker.get("state") if breaker else None


def _set_breaker_state(url_hash: str, state: str, ttl: int | None = None) -> None:
    if REDIS_CLIENT is not None:
        if ttl:
            REDIS_CLIENT.set(f"wh:breaker:{url_hash}", state, ex=ttl)
        else:
            REDIS_CLIENT.set(f"wh:breaker:{url_hash}", state)
    else:
        br = BREAKERS.setdefault(url_hash, {"failures": 0, "state": "closed", "opened_until": None})
        br["state"] = state
        br["opened_until"] = (
            datetime.now(timezone.utc) + timedelta(seconds=ttl) if ttl else None
        )


def _breaker_ttl(url_hash: str) -> int:
    if REDIS_CLIENT is not None:
        return int(REDIS_CLIENT.ttl(f"wh:breaker:{url_hash}"))
    br = BREAKERS.get(url_hash)
    if br and br.get("opened_until"):
        return int((br["opened_until"] - datetime.now(timezone.utc)).total_seconds())
    return -1


def _incr_failures(url_hash: str) -> int:
    if REDIS_CLIENT is not None:
        return int(REDIS_CLIENT.incr(f"wh:fail:{url_hash}"))
    br = BREAKERS.setdefault(url_hash, {"failures": 0, "state": "closed", "opened_until": None})
    br["failures"] += 1
    return br["failures"]


def _get_failures(url_hash: str) -> int:
    if REDIS_CLIENT is not None:
        return int(REDIS_CLIENT.get(f"wh:fail:{url_hash}") or 0)
    br = BREAKERS.get(url_hash)
    return br.get("failures", 0) if br else 0


def _reset_failures(url_hash: str) -> None:
    if REDIS_CLIENT is not None:
        REDIS_CLIENT.delete(f"wh:fail:{url_hash}")
    else:
        br = BREAKERS.get(url_hash)
        if br:
            br["failures"] = 0


def _clear_breaker(url_hash: str) -> None:
    if REDIS_CLIENT is not None:
        REDIS_CLIENT.delete(f"wh:breaker:{url_hash}")
    else:
        BREAKERS.pop(url_hash, None)


def _deliver(rule: NotificationRule, event: NotificationOutbox) -> None:
    """Send a notification according to its rule."""
    event_name = getattr(event, "event", None)
    formatter = FORMATTERS.get(event_name)
    payload = formatter(rule.channel, event.payload) if formatter else event.payload
    target = (rule.config or {}).get("target")
    if rule.channel == "console":
        print(json.dumps(payload))
    elif rule.channel == "webhook":
        url = (rule.config or {}).get("url")
        if not url:
            raise ValueError("webhook rule missing url")
        if not is_allowed_url(url):
            raise PermissionError("EGRESS_BLOCKED")

        secret = os.getenv("WEBHOOK_SIGNING_SECRET")
        body = json.dumps(payload, separators=(",", ":"))
        headers = {"Content-Type": "application/json"}
        if secret:
            ts = int(time.time())
            sig = sign(secret, ts, body.encode())
            headers["X-Webhook-Timestamp"] = str(ts)
            headers["X-Webhook-Signature"] = sig
            digest = sig.split("=", 1)[1]
            if REDIS_CLIENT is not None:
                try:
                    REDIS_CLIENT.setex(f"wh:nonce:{ts}:{digest}", 300, "1")
                except RedisError:  # pragma: no cover - redis failure
                    pass
        requests.post(
            url, data=body.encode(), headers=headers, timeout=5
        ).raise_for_status()
    elif rule.channel == "email":
        template = payload.get("template")
        vars = payload.get("vars", {})
        subject_tpl = payload.get("subject", "")
        if not template:
            raise ValueError("email payload missing template")
        subject, html = render_email(template, vars, subject_tpl)
        module = importlib.import_module(PROVIDER_REGISTRY["email"])
        module.send(event, {"subject": subject, "html": html}, target)
    elif rule.channel == "whatsapp":
        template = payload.get("template")
        if template:
            text = render_message(template, payload.get("vars", {}))
            module = importlib.import_module(PROVIDER_REGISTRY["whatsapp"])
            module.send(event, {"text": text}, target)
        else:
            module = importlib.import_module(PROVIDER_REGISTRY["whatsapp"])
            module.send(event, payload, target)
    elif rule.channel in PROVIDER_REGISTRY:
        module = importlib.import_module(PROVIDER_REGISTRY[rule.channel])
        module.send(event, payload, target)
    else:
        raise ValueError(f"unsupported channel {rule.channel}")


def _next_attempt(attempts: int) -> datetime:
    delay = BACKOFF[min(attempts - 1, len(BACKOFF) - 1)]
    jitter = random.uniform(0, delay * 0.1)
    return datetime.now(timezone.utc) + timedelta(seconds=delay + jitter)


def process_once(engine) -> None:
    """Attempt to deliver all queued notifications once."""
    max_attempts = int(os.getenv("OUTBOX_MAX_ATTEMPTS", "5"))
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        events = session.scalars(
            select(NotificationOutbox)
            .where(NotificationOutbox.status == "queued")
            .where(
                (NotificationOutbox.next_attempt_at == None)  # noqa: E711
                | (NotificationOutbox.next_attempt_at <= now)
            )
            .order_by(NotificationOutbox.created_at)
        ).all()
        for event in events:
            rule = session.get(NotificationRule, event.rule_id)
            if rule is None:
                event.status = "delivered"
                notifications_outbox_delivered_total.inc()
                session.add(event)
                continue

            url = (rule.config or {}).get("url") if rule.channel == "webhook" else None
            url_hash = _url_hash(url) if url else None
            if url_hash:
                state = _get_breaker_state(url_hash)
                if state == "open":
                    ttl = _breaker_ttl(url_hash)
                    if ttl > 0:
                        event.next_attempt_at = now + timedelta(seconds=ttl)
                    else:
                        event.next_attempt_at = now + timedelta(seconds=BREAKER_OPEN_SECS)
                    session.add(event)
                    webhook_breaker_state.labels(url_hash=url_hash).set(1)
                    continue
                failures = _get_failures(url_hash)
                if state is None and failures >= BREAKER_THRESHOLD:
                    _set_breaker_state(url_hash, "half")
                    webhook_breaker_state.labels(url_hash=url_hash).set(2)
                elif state == "half":
                    webhook_breaker_state.labels(url_hash=url_hash).set(2)
                else:
                    webhook_breaker_state.labels(url_hash=url_hash).set(0)
                webhook_attempts_total.labels(destination=url).inc()

            try:
                _deliver(rule, event)
            except Exception as exc:
                if url_hash:
                    webhook_failures_total.labels(destination=url).inc()
                    failures = _incr_failures(url_hash)
                    state = _get_breaker_state(url_hash)
                    if state == "half" or failures >= BREAKER_THRESHOLD:
                        _set_breaker_state(url_hash, "open", BREAKER_OPEN_SECS)
                        webhook_breaker_state.labels(url_hash=url_hash).set(1)
                    else:
                        webhook_breaker_state.labels(url_hash=url_hash).set(0)
                if str(exc) == "EGRESS_BLOCKED":
                    session.add(
                        NotificationDLQ(
                            original_id=event.id,
                            rule_id=event.rule_id,
                            payload=event.payload,
                            error=str(exc),
                        )
                    )
                    notifications_outbox_failed_total.inc()
                    session.delete(event)
                    continue
                event.attempts += 1
                if event.attempts > max_attempts:
                    session.add(
                        NotificationDLQ(
                            original_id=event.id,
                            rule_id=event.rule_id,
                            payload=event.payload,
                            error=f"max attempts exceeded: {exc}",
                        )
                    )
                    notifications_outbox_failed_total.inc()
                    session.delete(event)
                else:
                    event.next_attempt_at = _next_attempt(event.attempts)
                    session.add(event)
                continue
            if url_hash:
                _reset_failures(url_hash)
                _clear_breaker(url_hash)
                webhook_breaker_state.labels(url_hash=url_hash).set(0)
            event.status = "delivered"
            notifications_outbox_delivered_total.inc()
            session.add(event)
        session.commit()


def main() -> None:
    init_sentry()
    db_url = os.environ["POSTGRES_URL"]
    poll = int(os.getenv("POLL_INTERVAL", "5"))
    engine = create_engine(db_url)
    while True:
        try:
            process_once(engine)
        except Exception as exc:  # pragma: no cover - defensive
            capture_exception(exc)
        time.sleep(poll)


if __name__ == "__main__":
    main()
