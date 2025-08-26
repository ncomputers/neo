"""Abuse guard checks for guest-facing endpoints.

Provides IP cooldown after repeated rejections, User-Agent denylist checks, and
simple geo sanity hints comparing reported request city against the tenant
city. Raise ``HTTPException`` with HTTP 429 when abuse is detected.
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..utils.responses import err
from . import blocklist
from .ua_denylist import is_denied


def _geo_hint(request: Request) -> str | None:
    """Return mismatch hint between ``X-Geo-City`` and ``X-Tenant-City`` headers."""
    tenant_city = request.headers.get("X-Tenant-City")
    client_city = request.headers.get("X-Geo-City")
    if tenant_city and client_city and tenant_city.lower() != client_city.lower():
        return f"{client_city} != {tenant_city}"
    return None


async def guard(request: Request, tenant: str, redis: Redis) -> None:
    """Raise ``HTTPException`` if the request should be cooled down.

    The check denies requests from denylisted user agents or IPs that are
    currently cooled down due to prior rejections.
    """

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("User-Agent")
    hint = _geo_hint(request)
    if is_denied(ua):
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=err("UA_BLOCKED", "TooManyRequests", hint=hint),
        )
    if await blocklist.is_blocked(redis, tenant, ip):
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=err("IP_BLOCKED", "TooManyRequests", hint=hint),
        )
