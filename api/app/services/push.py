from __future__ import annotations

"""Web Push subscription storage and outbox enqueueing."""

import json
import logging

from ..db import SessionLocal
from ..models_master import NotificationOutbox, NotificationRule

logger = logging.getLogger("push")


async def save_subscription(tenant: str, table: str, subscription: dict) -> None:
    """Persist a Web Push ``subscription`` for ``tenant`` and ``table``."""
    from ..main import redis_client  # lazy import to avoid circular deps

    key = f"rt:push:{tenant}:{table}"
    await redis_client.set(key, json.dumps(subscription))


async def notify_ready(tenant: str, table: str, order_id: int) -> None:
    """Queue a stub Web Push notification when an order is ready."""
    from ..main import redis_client  # lazy import to avoid circular deps

    key = f"rt:push:{tenant}:{table}"
    try:
        data = await redis_client.get(key)
    except Exception:  # pragma: no cover - best effort
        return
    if not data:
        return

    payload = {
        "title": "Order ready",
        "body": f"Order {order_id} is ready",
        "table_code": table,
        "order_no": order_id,
    }

    with SessionLocal() as session:
        rule = NotificationRule(channel="webpush", config={})
        session.add(rule)
        session.flush()
        session.add(NotificationOutbox(rule_id=rule.id, payload=payload))
        session.commit()

    logger.info("web-push queued")
