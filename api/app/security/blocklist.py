# blocklist.py
"""Redis-backed helpers for tracking IP rejections and blocks."""

from __future__ import annotations

from redis.asyncio import Redis

BLOCK_KEY = "blocklist:{tenant}:ip:{ip}"
REJ_KEY = "rej:{tenant}:ip:{ip}"


async def add_rejection(redis: Redis, tenant: str, ip: str, ttl: int = 86400) -> int:
    """Increment rejection counter for ``ip`` within ``tenant`` and return count.

    The counter is automatically expired after ``ttl`` seconds (default 1 day)
    so that rejections are counted within a rolling window.
    """
    key = REJ_KEY.format(tenant=tenant, ip=ip)
    count = await redis.incr(key)
    await redis.expire(key, ttl)
    return count


async def is_blocked(redis: Redis, tenant: str, ip: str) -> bool:
    """Check if ``ip`` is currently blocked for ``tenant``."""
    return bool(await redis.exists(BLOCK_KEY.format(tenant=tenant, ip=ip)))


async def block_ip(redis: Redis, tenant: str, ip: str, ttl: int = 86400) -> None:
    """Block ``ip`` for ``tenant`` for the given ``ttl`` (default 1 day)."""
    await redis.set(BLOCK_KEY.format(tenant=tenant, ip=ip), 1, ex=ttl)


async def clear_ip(redis: Redis, tenant: str, ip: str) -> None:
    """Remove block and rejection counters for ``ip`` within ``tenant``."""
    await redis.delete(
        BLOCK_KEY.format(tenant=tenant, ip=ip), REJ_KEY.format(tenant=tenant, ip=ip)
    )
