from __future__ import annotations

"""Printer agent heartbeat and retry queue metrics for KDS."""


import logging
from datetime import datetime, timezone
from typing import Tuple

HEARTBEAT_KEY = "print:hb:{tenant}"
RETRY_QUEUE_KEY = "print:retry:{tenant}"
DEFAULT_TIMEOUT = 60 * 5  # 5 minutes



async def check(
    redis,
    tenant: str,
    timeout: int = DEFAULT_TIMEOUT,
    now: datetime | None = None,
) -> Tuple[bool, int, int]:
    """Return heartbeat stale flag, retry queue length and oldest age.

    ``redis`` is an ``aioredis`` compatible client. ``timeout`` is the maximum
    allowed seconds between heartbeats. ``now`` is only used for tests.

    """
    if now is None:
        now = datetime.now(timezone.utc)

    hb_key = HEARTBEAT_KEY.format(tenant=tenant)
    raw = await redis.get(hb_key)
    stale = True
    if raw:
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            last = datetime.fromisoformat(raw)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            stale = (now - last).total_seconds() > timeout
        except ValueError:
            stale = True
    if stale:
        logging.warning("printer heartbeat stale", extra={"tenant": tenant})

    q_key = RETRY_QUEUE_KEY.format(tenant=tenant)
    qlen = await redis.llen(q_key)
    oldest_age = 0
    if qlen:
        head = await redis.lindex(q_key, 0)
        if head:
            if isinstance(head, bytes):
                head = head.decode()
            try:
                ts = datetime.fromisoformat(head)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                oldest_age = int((now - ts).total_seconds())
            except ValueError:
                oldest_age = 0
    return stale, int(qlen), oldest_age

