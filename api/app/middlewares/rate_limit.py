from __future__ import annotations

import time
import uuid
from typing import Callable

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..utils.responses import err


class SlidingWindowRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit sensitive endpoints using a simple sliding window."""

    def __init__(self, app: Callable, limit: int = 5, window: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        if request.url.path not in {"/login/pin", "/auth/refresh"}:
            return await call_next(request)
        redis: Redis = request.app.state.redis
        key = f"ratelimit:{request.url.path}:{request.client[0]}"
        now = int(time.time())
        pipe = redis.pipeline()
        pipe.zadd(key, {str(uuid.uuid4()): now})
        pipe.zremrangebyscore(key, 0, now - self.window)
        pipe.zcard(key)
        pipe.expire(key, self.window)
        _, _, count, _ = await pipe.execute()
        if count and count > self.limit:
            retry = await redis.ttl(key)
            headers = {"Retry-After": str(retry if retry > 0 else self.window)}
            return JSONResponse(
                err("RATE_LIMIT", "RateLimitExceeded"),
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
            )
        return await call_next(request)
