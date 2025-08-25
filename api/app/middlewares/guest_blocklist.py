"""Block abusive guest, hotel, and counter POST requests based on IP blocklist."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..security import blocklist
from ..utils.responses import err
from .guest_utils import _is_guest_post


class GuestBlocklistMiddleware(BaseHTTPMiddleware):
    """Deny blocked IPs for guest, hotel, and counter POST endpoints."""

    async def dispatch(self, request: Request, call_next):
        if _is_guest_post(request.url.path, request.method):
            ip = request.client.host if request.client else "unknown"
            tenant = request.headers.get("X-Tenant-ID", "demo")
            redis = request.app.state.redis
            if await blocklist.is_blocked(redis, tenant, ip):
                return JSONResponse(
                    err("IP_BLOCKED", "TooManyRequests"),
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                )
        return await call_next(request)
