"""Simple helpers for caching IP reputation scores."""

from __future__ import annotations

from redis.asyncio import Redis

REP_KEY = "rep:ip:{ip}"


async def mark_bad(redis: Redis, ip: str, ttl: int = 3600) -> None:
    """Mark ``ip`` as having bad reputation for ``ttl`` seconds."""
    await redis.set(REP_KEY.format(ip=ip), "bad", ex=ttl)


async def is_bad(redis: Redis, ip: str) -> bool:
    """Return ``True`` if ``ip`` was previously marked bad."""
    value = await redis.get(REP_KEY.format(ip=ip))
    return value == "bad" or value == b"bad"
