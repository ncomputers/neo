from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Tuple

HEARTBEAT_KEY = "print:hb:{tenant}"
QUEUE_KEY = "print:q:{tenant}"
DEFAULT_TIMEOUT = 60


async def check(redis, tenant: str, timeout: int = DEFAULT_TIMEOUT,
                now: datetime | None = None) -> Tuple[bool, int]:
    """Return printer heartbeat stale flag and retry queue length.

    ``redis`` is an ``aioredis`` compatible client. ``timeout`` is the
    maximum allowed seconds between heartbeats. ``now`` is only used for
    tests.
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

    q_key = QUEUE_KEY.format(tenant=tenant)
    qlen = await redis.llen(q_key)
    return stale, int(qlen)
