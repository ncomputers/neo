"""Guest rate limiting middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS

from ..security import blocklist, ratelimit
from ..utils.responses import err


class GuestRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit guest-facing `/g/*` routes."""

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/g/"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        redis = request.app.state.redis

        if request.method == "POST" and await blocklist.is_blocked(redis, ip):
            return JSONResponse(
                err("SUB_403", "Blocked"), status_code=HTTP_403_FORBIDDEN
            )

        allowed = await ratelimit.allow(redis, ip, "guest", rate_per_min=60, burst=100)
        if not allowed:
            return JSONResponse(
                err("RATELIMIT_429", "TooManyRequests"),
                status_code=HTTP_429_TOO_MANY_REQUESTS,
            )
        return await call_next(request)
