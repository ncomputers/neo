"""Request idempotency middleware for order routes."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from ..utils.responses import err


_ORDER_PATH_RE = re.compile(r"^/(g|h|c)/.+/order$")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Cache and enforce idempotent POSTs to order routes."""

    def __init__(self, app, ttl: int = 3600) -> None:
        super().__init__(app)
        self.ttl = ttl

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if not _ORDER_PATH_RE.match(path):
            return await call_next(request)

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return JSONResponse(
                err("IDEMP_KEY_REQUIRED", "Idempotency-Key header required"),
                status_code=HTTP_400_BAD_REQUEST,
            )

        tenant = request.headers.get("X-Tenant-ID", "default")
        cache_key = f"idem:{tenant}:{idem_key}"
        redis = request.app.state.redis

        body_bytes = await request.body()
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        request._body = body_bytes  # allow downstream access

        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            if data["hash"] == body_hash:
                return JSONResponse(data["response"])
            return JSONResponse(
                err("IDEMP_MISMATCH", "Payload differs from original request"),
                status_code=HTTP_409_CONFLICT,
            )

        response = await call_next(request)

        if response.status_code == 200:
            chunks = [chunk async for chunk in response.body_iterator]
            body = b"".join(chunks)

            async def _replay():
                for chunk in chunks:
                    yield chunk

            response.body_iterator = _replay()
            try:
                resp_json = json.loads(body)
            except Exception:  # pragma: no cover - non-JSON responses
                resp_json = None
            if resp_json is not None:
                await redis.set(
                    cache_key,
                    json.dumps({"hash": body_hash, "response": resp_json}),
                    ex=self.ttl,
                )
        return response
