"""Rate limiting middleware for guest, hotel, and counter POST requests."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..security import ratelimit
from ..utils import ratelimits
from ..utils.responses import rate_limited
from .guest_utils import _is_guest_post


class GuestRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit guest POST endpoints for guest, hotel, and counter routes."""

    async def dispatch(self, request: Request, call_next):
        if not _is_guest_post(request.url.path, request.method):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        redis = request.app.state.redis

        policy = ratelimits.guest_order()
        allowed = await ratelimit.allow(
            redis, ip, "guest", rate_per_min=policy.rate_per_min, burst=policy.burst
        )
        if not allowed:
            retry_after = await redis.ttl(f"ratelimit:{ip}:guest")
            return rate_limited(retry_after)
        return await call_next(request)
