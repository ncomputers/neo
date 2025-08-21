# blocklist.py
"""Redis-backed helpers for tracking IP rejections and blocks."""

from __future__ import annotations

from redis.asyncio import Redis

BLOCK_KEY = "blocklist:ip:{ip}"
REJ_KEY = "rej:ip:{ip}"


async def add_rejection(redis: Redis, ip: str, ttl: int = 86400) -> int:
    """Increment rejection counter for an IP and return the new count.

    The counter is automatically expired after ``ttl`` seconds (default 1 day)
    so that rejections are counted within a rolling window.
    """
    key = REJ_KEY.format(ip=ip)
    count = await redis.incr(key)
    await redis.expire(key, ttl)
    return count


async def is_blocked(redis: Redis, ip: str) -> bool:
    """Check if the IP is currently blocked."""
    return bool(await redis.exists(BLOCK_KEY.format(ip=ip)))


async def block_ip(redis: Redis, ip: str, ttl: int = 86400) -> None:
    """Block the IP for the given TTL (default 1 day)."""
    await redis.set(BLOCK_KEY.format(ip=ip), 1, ex=ttl)


async def clear_ip(redis: Redis, ip: str) -> None:
    """Remove block and rejection counters for an IP."""
    await redis.delete(BLOCK_KEY.format(ip=ip), REJ_KEY.format(ip=ip))
