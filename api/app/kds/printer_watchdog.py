from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Tuple

HEARTBEAT_KEY = "print:hb:{tenant}"
QUEUE_KEY = "print:q:{tenant}"
DEFAULT_TIMEOUT = 60 * 5  # seconds


def _job_age(raw: str, now: datetime) -> int:
    """Return age in seconds for a queue item payload.

    ``raw`` may contain an ISO timestamp under ``ts`` key (JSON) or
    start with a timestamp followed by a separator (``|``).
    """
    ts: str | None = None
    try:
        obj = json.loads(raw)
        ts = obj.get("ts")
    except Exception:
        parts = raw.split("|", 1)
        if len(parts) > 1:
            ts = parts[0]
    if ts:
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int((now - dt).total_seconds())
        except ValueError:
            return 0
    return 0


async def check(
    redis,
    tenant: str,
    timeout: int = DEFAULT_TIMEOUT,
    now: datetime | None = None,
) -> Tuple[bool, int, int]:
    """Return printer heartbeat stale flag, retry queue length and oldest age.

    ``redis`` is an ``aioredis`` compatible client. ``timeout`` is the
    maximum allowed seconds between heartbeats. ``now`` is only used for
    tests. Age is reported in seconds and is ``0`` if the queue is empty
    or timestamps cannot be parsed.
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
    age = 0
    if qlen:
        oldest = await redis.lindex(q_key, -1)
        if isinstance(oldest, bytes):
            oldest = oldest.decode()
        age = _job_age(oldest, now)
    return stale, int(qlen), age
