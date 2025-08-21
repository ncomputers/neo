# order_rejection.py
"""Hooks for handling order rejections."""

from redis.asyncio import Redis

from .. import security


async def on_rejected(ip: str, redis: Redis) -> None:
    """Record a rejected IP in the blocklist.

    After three rejections within a 24 hour window the IP is blocked for one
    day and subsequent guest requests will be denied.
    """
    count = await security.blocklist.add_rejection(redis, ip)
    if count >= 3:
        await security.blocklist.block_ip(redis, ip)
