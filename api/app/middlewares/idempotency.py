"""Idempotency middleware for order placement endpoints."""

from __future__ import annotations

import json
import hashlib
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..utils.responses import err


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Cache successful order responses keyed by request body hash."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if (
            request.method != "POST"
            or not path.endswith("/order")
            or not (path.startswith("/g/") or path.startswith("/h/") or path.startswith("/c/"))
        ):
            return await call_next(request)

        tenant = request.headers.get("X-Tenant-ID", "default")

        key = request.headers.get("Idempotency-Key")
        if not key:
            return JSONResponse(
                err("IDEMP_REQUIRED", "Idempotency-Key required"), status_code=400
            )

        body_bytes = await request.body()
        body_hash = hashlib.sha256(body_bytes).hexdigest()

        async def receive() -> dict:
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(request.scope, receive)

        redis = request.app.state.redis
        redis_key = f"idem:{tenant}:{key}"
        cached = await redis.get(redis_key)
        if cached:
            payload = json.loads(cached)
            if payload.get("body_hash") != body_hash:
                return JSONResponse(
                    err("IDEMP_MISMATCH", "Key reused with different body"), status_code=400
                )
            return JSONResponse(payload.get("response"))

        response = await call_next(request)
        resp_body = b""
        async for chunk in response.body_iterator:
            resp_body += chunk
        # rebuild response so downstream receives body
        response = Response(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
            background=response.background,
        )

        if response.status_code == 200:
            try:
                resp_json = json.loads(resp_body.decode())
            except Exception:
                resp_json = None
            data = {"body_hash": body_hash, "response": resp_json}
            await redis.set(redis_key, json.dumps(data))

        return response
