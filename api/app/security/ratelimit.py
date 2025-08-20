"""Token bucket helpers backed by Redis.

This module exposes a single :func:`allow` helper implementing a minimal
Redis-based token bucket.  It relies only on ``INCR`` and ``EXPIRE`` and thus
keeps state in a single counter per IP/key pair.  The approach approximates a
leaky bucket: each request increments a counter and the counter automatically
"leaks" once the TTL expires.  ``burst`` defines the bucket capacity while
``rate_per_min`` controls how fast the bucket refills.

Algorithm
=========
1. Compose a bucket key ``ratelimit:{ip}:{key}``.
2. ``INCR`` the counter.  If this is the first hit, set ``EXPIRE`` to a window
   of ``burst / rate_per_min * 60`` seconds.  The window roughly represents the
   time required to fully refill the bucket at the target rate.
3. If the counter exceeds ``burst`` the request is denied.
4. Once the key expires, the count resets, slowly leaking past requests.

This simplistic design does not require Lua scripts or complex data structures
and is sufficient for coarse rate limiting in front of higher level policies or
blocklists.
"""

from __future__ import annotations

from math import ceil
from redis.asyncio import Redis


async def allow(
    redis: Redis,
    ip: str,
    key: str,
    rate_per_min: int = 60,
    burst: int = 100,
) -> bool:
    """Return ``True`` if the request is within the rate limit.

    Parameters
    ----------
    redis:
        Redis connection used for accounting.
    ip:
        Client IP address.
    key:
        Additional bucket key (e.g. an endpoint name).
    rate_per_min:
        Desired sustained rate in requests per minute.
    burst:
        Maximum burst size allowed before throttling.
    """

    bucket = f"ratelimit:{ip}:{key}"
    count = await redis.incr(bucket)
    if count == 1:
        # Time for the bucket to completely refill at the desired rate.
        window = ceil(burst / rate_per_min * 60)
        await redis.expire(bucket, window)
    return count <= burst
