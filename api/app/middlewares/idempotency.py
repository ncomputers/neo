from __future__ import annotations

import base64
import hashlib
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..routes_metrics import idempotency_conflicts_total, idempotency_hits_total


class IdempotencyMetricsMiddleware(BaseHTTPMiddleware):
    """Track idempotency key usage and conflicts."""

    async def dispatch(self, request: Request, call_next):
        has_key = "Idempotency-Key" in request.headers
        response = await call_next(request)
        if has_key:
            idempotency_hits_total.inc()
            if response.status_code == 409:
                idempotency_conflicts_total.inc()

        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Cache responses for POSTs with an ``Idempotency-Key`` header.

    Keys are stored in Redis for a short duration to avoid creating duplicate
    orders or bills when clients retry requests on flaky networks.
    """

    async def dispatch(self, request: Request, call_next):
        if (
            request.method == "POST"
            and request.url.path.startswith(("/g/", "/h/", "/c/", "/api/outlet/"))
            and (key := request.headers.get("Idempotency-Key"))
        ):
            redis = request.app.state.redis
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            cache_key = f"idem:{request.url.path}:{key_hash}"
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                body = base64.b64decode(data["body"])
                return Response(
                    content=body,
                    status_code=data["status"],
                    headers=data.get("headers"),
                    media_type=data.get("media_type", "application/json"),
                )

            response = await call_next(request)
            body = b"".join([section async for section in response.body_iterator])
            headers = dict(response.headers)
            payload = {
                "status": response.status_code,
                "body": base64.b64encode(body).decode(),
                "headers": headers,
                "media_type": response.media_type,
            }
            await redis.set(cache_key, json.dumps(payload), ex=86400)
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        return await call_next(request)
