from __future__ import annotations

"""Web Push subscription storage and stubs."""

import json
import logging


logger = logging.getLogger("push")


async def save_subscription(tenant: str, table: str, subscription: dict) -> None:
    """Persist a Web Push ``subscription`` for ``tenant`` and ``table``."""
    from ..main import redis_client  # lazy import to avoid circular deps

    key = f"rt:push:{tenant}:{table}"
    await redis_client.set(key, json.dumps(subscription))


async def notify_ready(tenant: str, table: str, order_id: int) -> None:
    """Log a stub Web Push notification when an order is ready."""
    from ..main import redis_client  # lazy import to avoid circular deps

    key = f"rt:push:{tenant}:{table}"
    try:
        data = await redis_client.get(key)
    except Exception:  # pragma: no cover - best effort
        return
    if not data:
        return
    logger.info("web-push queued")
