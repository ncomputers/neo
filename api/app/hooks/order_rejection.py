# order_rejection.py
"""Hooks for handling order rejections."""

from redis.asyncio import Redis

from .. import security


async def on_rejected(ip: str, redis: Redis) -> None:
    """Record a rejected IP in the blocklist."""
    await security.blocklist.add_rejection(redis, ip)
