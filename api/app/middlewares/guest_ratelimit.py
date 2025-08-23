"""Rate limiting middleware for guest, hotel, and counter POST requests."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..security import ratelimit
from ..utils.responses import err
from .guest_utils import _is_guest_post


class GuestRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit guest POST endpoints for guest, hotel, and counter routes."""

    async def dispatch(self, request: Request, call_next):
        if not _is_guest_post(request.url.path, request.method):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        redis = request.app.state.redis

        allowed = await ratelimit.allow(redis, ip, "guest", rate_per_min=60, burst=100)
        if not allowed:
            retry_after = await redis.ttl(f"ratelimit:{ip}:guest")
            return JSONResponse(
                err("RATELIMITED", "TooManyRequests", {"retry_after": max(retry_after, 0)}),
                status_code=HTTP_429_TOO_MANY_REQUESTS,
            )
        return await call_next(request)
