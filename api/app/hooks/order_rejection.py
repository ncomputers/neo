# order_rejection.py
"""Hooks for handling order rejections."""

from redis.asyncio import Redis

from .. import security
from ..audit import log_event


async def on_rejected(tenant: str, ip: str, redis: Redis) -> None:
    """Record a rejected IP for ``tenant`` and block after repeated failures.

    After three rejections within a 24 hour window the IP is cooled down for
    fifteen minutes and subsequent guest requests will be denied during this
    period.
    """
    count = await security.blocklist.add_rejection(redis, tenant, ip)
    if count >= 3:
        await security.blocklist.block_ip(redis, tenant, ip, ttl=900)
        log_event("system", "block_ip", f"{tenant}:{ip}")
