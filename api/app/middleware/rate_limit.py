from __future__ import annotations

import os
import re
import time
import uuid
from typing import Callable

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..utils.rate_limit import rate_limited

_TIME_UNITS = {"s": 1, "m": 60, "h": 3600}


def _parse_limit(value: str, default: tuple[int, int]) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)/(\d+)([smh])", value)
    if not match:
        return default
    count, span, unit = match.groups()
    return int(count), int(span) * _TIME_UNITS[unit]


class SlidingWindowRateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter for authentication endpoints."""

    def __init__(self, app: Callable) -> None:
        super().__init__(app)
        login = _parse_limit(os.getenv("RATE_LIMIT_LOGIN", "10/5m"), (10, 300))
        refresh = _parse_limit(os.getenv("RATE_LIMIT_REFRESH", "60/5m"), (60, 300))
        self.limits = {
            "/login/pin": login,
            "/auth/login-pin": login,
            "/auth/refresh": refresh,
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        if request.url.path not in self.limits:
            return await call_next(request)
        limit, window = self.limits[request.url.path]
        redis: Redis = request.app.state.redis
        ip = request.client[0] if request.client else "unknown"
        tenant = request.headers.get("X-Tenant-ID", "-")
        key = f"ratelimit:{request.url.path}:{tenant}:{ip}"
        now = int(time.time())
        pipe = redis.pipeline()
        pipe.zadd(key, {str(uuid.uuid4()): now})
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.expire(key, window)
        _, _, count, _ = await pipe.execute()
        if count and count > limit:
            retry = await redis.ttl(key)
            retry_after = retry if retry and retry > 0 else window
            response = rate_limited(retry_after)
            response.headers["Retry-After"] = str(retry_after)
            return response
        return await call_next(request)
