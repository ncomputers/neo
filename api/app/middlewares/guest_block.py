"""Block abusive guest, hotel, and counter POST requests based on IP blocklist."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..security import blocklist, ip_reputation
from ..security.ua_denylist import is_denied
from ..utils.responses import err
from .guest_utils import _is_guest_post


def _geo_hint(request: Request) -> str | None:
    """Return a hint if request city mismatches tenant city."""
    tenant_city = request.headers.get("X-Tenant-City")
    client_city = request.headers.get("X-Geo-City")
    if tenant_city and client_city and tenant_city.lower() != client_city.lower():
        return f"{client_city} != {tenant_city}"
    return None


class GuestBlockMiddleware(BaseHTTPMiddleware):
    """Deny blocked IPs for guest, hotel, and counter POST endpoints."""

    async def dispatch(self, request: Request, call_next):
        if _is_guest_post(request.url.path, request.method):
            ip = request.client.host if request.client else "unknown"
            tenant = request.headers.get("X-Tenant-ID", "demo")
            redis = request.app.state.redis
            ua = request.headers.get("User-Agent")
            if is_denied(ua):
                return JSONResponse(
                    err("UA_BLOCKED", "TooManyRequests", hint=_geo_hint(request)),
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                )
            if await ip_reputation.is_bad(redis, ip) or await blocklist.is_blocked(
                redis, tenant, ip
            ):
                return JSONResponse(
                    err("IP_BLOCKED", "TooManyRequests", hint=_geo_hint(request)),
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                )
        return await call_next(request)
