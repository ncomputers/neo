#!/usr/bin/env python3
"""Background worker to deliver queued notifications.

Environment variables:
- POSTGRES_URL: SQLAlchemy URL for the master database.
- POLL_INTERVAL: Seconds between polling attempts (default: 5).
- OUTBOX_MAX_ATTEMPTS: Max delivery attempts before DLQ (default: 5).
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import random
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
    webhook_breaker_state,
    webhook_failures_total,
)

PROVIDER_REGISTRY = {
    "whatsapp": os.getenv("ALERTS_WHATSAPP_PROVIDER", "app.providers.whatsapp_stub"),
    "sms": os.getenv("ALERTS_SMS_PROVIDER", "app.providers.sms_stub"),
    "email": os.getenv("ALERTS_EMAIL_PROVIDER", "app.providers.email_stub"),
    "webpush": os.getenv("ALERTS_WEBPUSH_PROVIDER", "app.providers.webpush_stub"),
    "slack": os.getenv("ALERTS_SLACK_PROVIDER", "app.providers.slack_stub"),
}

BACKOFF = [1, 5, 30, 120, 600]  # seconds: 1s, 5s, 30s, 2m, 10m

CB_FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "8"))
CB_COOLDOWN_SEC = int(os.getenv("CB_COOLDOWN_SEC", "600"))
CB_HALFOPEN_TRIALS = int(os.getenv("CB_HALFOPEN_TRIALS", "1"))
CB_KEY_PREFIX = os.getenv("CB_KEY_PREFIX", "cb:")

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


def _cb_key(url_hash: str, suffix: str) -> str:
    return f"{CB_KEY_PREFIX}{url_hash}:{suffix}"


def breaker_state(r, url_hash: str, now: int | None = None) -> tuple[str, int]:
    """Return breaker state and remaining cooldown."""
    now = now or int(time.time())
    if r is None:
        br = BREAKERS.get(url_hash, {})
        state = br.get("state", "closed")
        remaining = max(0, br.get("until", 0) - now) if state == "open" else 0
        return state, remaining
    state = r.get(_cb_key(url_hash, "state"))
    state_str = state.decode() if state else "closed"
    if state_str == "open":
        until = int(r.get(_cb_key(url_hash, "until")) or 0)
        return state_str, max(0, until - now)
    return state_str, 0


def breaker_on_success(r, url_hash: str) -> None:
    if r is None:
        BREAKERS.pop(url_hash, None)
        return
    pipe = r.pipeline()
    pipe.set(_cb_key(url_hash, "state"), "closed")
    pipe.delete(_cb_key(url_hash, "fails"))
    pipe.delete(_cb_key(url_hash, "until"))
    pipe.delete(_cb_key(url_hash, "trial"))
    pipe.execute()


def breaker_on_failure(
    r, url_hash: str, threshold: int, cooldown: int, now: int
) -> int:
    if r is None:
        br = BREAKERS.setdefault(
            url_hash, {"state": "closed", "fails": 0, "until": 0, "trial": 0}
        )
        br["fails"] = br.get("fails", 0) + 1
        fails = br["fails"]
        if fails >= threshold:
            br["state"] = "open"
            br["until"] = now + cooldown
        return fails
    fails = int(r.incr(_cb_key(url_hash, "fails")))
    if fails >= threshold:
        pipe = r.pipeline()
        pipe.set(_cb_key(url_hash, "state"), "open")
        pipe.set(_cb_key(url_hash, "until"), now + cooldown)
        pipe.delete(_cb_key(url_hash, "trial"))
        pipe.execute()
    return fails


def breaker_allow(r, url_hash: str, now: int) -> tuple[bool, str]:
    if r is None:
        br = BREAKERS.setdefault(
            url_hash, {"state": "closed", "fails": 0, "until": 0, "trial": 0}
        )
        state = br.get("state", "closed")
        if state == "open":
            if now < br.get("until", 0):
                return False, "open"
            br["state"] = "half_open"
            br["trial"] = 0
            return True, "half_open"
        if state == "half_open":
            trial = br.get("trial", 0)
            if trial >= CB_HALFOPEN_TRIALS:
                br["state"] = "open"
                br["until"] = now + CB_COOLDOWN_SEC
                return False, "open"
            br["trial"] = trial + 1
            return True, "half_open"
        return True, state

    state = r.get(_cb_key(url_hash, "state"))
    state_str = state.decode() if state else "closed"
    if state_str == "open":
        until = int(r.get(_cb_key(url_hash, "until")) or 0)
        if now < until:
            return False, "open"
        pipe = r.pipeline()
        pipe.set(_cb_key(url_hash, "state"), "half_open")
        pipe.set(_cb_key(url_hash, "trial"), 0)
        pipe.execute()
        return True, "half_open"
    if state_str == "half_open":
        trial = int(r.get(_cb_key(url_hash, "trial")) or 0)
        if trial >= CB_HALFOPEN_TRIALS:
            pipe = r.pipeline()
            pipe.set(_cb_key(url_hash, "state"), "open")
            pipe.set(_cb_key(url_hash, "until"), now + CB_COOLDOWN_SEC)
            pipe.execute()
            return False, "open"
        r.incr(_cb_key(url_hash, "trial"))
        return True, "half_open"
    return True, state_str


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
            now_ts = int(time.time())
            if url_hash:
                allowed, st = breaker_allow(REDIS_CLIENT, url_hash, now_ts)
                webhook_breaker_state.labels(url_hash=url_hash).set(
                    {"closed": 0, "open": 1, "half_open": 2}[st]
                )
                if not allowed:
                    _, remaining = breaker_state(REDIS_CLIENT, url_hash, now_ts)
                    wait = remaining if remaining > 0 else CB_COOLDOWN_SEC
                    event.next_attempt_at = now + timedelta(seconds=wait)
                    session.add(event)
                    continue
                webhook_attempts_total.labels(destination=url_hash).inc()

            try:
                _deliver(rule, event)
            except Exception as exc:
                if url_hash:
                    webhook_failures_total.labels(destination=url_hash).inc()
                    breaker_on_failure(
                        REDIS_CLIENT,
                        url_hash,
                        CB_FAILURE_THRESHOLD,
                        CB_COOLDOWN_SEC,
                        now_ts,
                    )
                    state, _ = breaker_state(REDIS_CLIENT, url_hash, now_ts)
                    webhook_breaker_state.labels(url_hash=url_hash).set(
                        {"closed": 0, "open": 1, "half_open": 2}[state]
                    )
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
            else:
                if url_hash:
                    breaker_on_success(REDIS_CLIENT, url_hash)
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
