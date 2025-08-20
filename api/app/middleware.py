# middleware.py

"""Rate limiting middleware backed by Redis."""

from __future__ import annotations

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_403_FORBIDDEN


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Block IPs after repeated failing requests."""

    def __init__(self, app, limit: int = 3):
        super().__init__(app)
        self.limit = limit

    async def dispatch(self, request: Request, call_next):
        redis: Redis = request.app.state.redis
        client = request.client[0] if request.client else "unknown"
        if await redis.sismember("blocklist:ip", client):
            return Response(status_code=HTTP_403_FORBIDDEN)
        response = await call_next(request)
        if response.status_code >= 400 and request.url.path.startswith("/login"):
            key = f"ratelimit:ip:{client}"
            count = await redis.incr(key)
            if count >= self.limit:
                await redis.sadd("blocklist:ip", client)
        return response
