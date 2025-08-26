from __future__ import annotations

from typing import Any, Tuple

MAX_ATTEMPTS = 5
FAIL_WINDOW = 10 * 60  # 10 minutes
LOCK_TTL = 15 * 60  # 15 minutes


def keys(tenant: str, username: str, ip: str) -> Tuple[str, str, str]:
    """Return Redis keys for lock, status and fail counters."""
    return (
        f"pin:lock:{tenant}:{username}:{ip}",
        f"pin:lockstatus:{tenant}:{username}:{ip}",
        f"pin:fail:{tenant}:{username}:{ip}",
    )


def lock_key(tenant: str, username: str, ip: str) -> str:
    return keys(tenant, username, ip)[0]


async def is_locked(redis: Any, tenant: str, username: str, ip: str) -> bool:
    """Return ``True`` if the user is currently locked out."""
    return bool(await redis.exists(lock_key(tenant, username, ip)))


async def register_failure(redis: Any, tenant: str, username: str, ip: str) -> bool:
    """Record a failed attempt and return ``True`` if lockout is triggered."""
    lock, status, fail = keys(tenant, username, ip)
    count = await redis.incr(fail)
    await redis.expire(fail, FAIL_WINDOW)
    if count >= MAX_ATTEMPTS:
        await redis.set(lock, 1, ex=LOCK_TTL)
        await redis.set(status, 1)
        await redis.delete(fail)
        return True
    return False


async def reset(redis: Any, tenant: str, username: str) -> None:
    """Clear any lockout state for ``username`` in ``tenant``."""
    async for key in redis.scan_iter(f"pin:lock:{tenant}:{username}:*"):
        await redis.delete(key)
    async for key in redis.scan_iter(f"pin:lockstatus:{tenant}:{username}:*"):
        await redis.delete(key)
    async for key in redis.scan_iter(f"pin:fail:{tenant}:{username}:*"):
        await redis.delete(key)


__all__ = [
    "MAX_ATTEMPTS",
    "FAIL_WINDOW",
    "LOCK_TTL",
    "keys",
    "lock_key",
    "is_locked",
    "register_failure",
    "reset",
]
