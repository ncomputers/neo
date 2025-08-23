from __future__ import annotations

import json
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_400_BAD_REQUEST

from ..routes_metrics import idempotency_hits_total, idempotency_conflicts_total
from ..utils.responses import err


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
            and request.url.path.startswith(("/g/", "/h/", "/c/"))
            and (key := request.headers.get("Idempotency-Key"))
        ):
            if len(key) > 128 or not (
                re.fullmatch(r"[0-9a-fA-F]+", key)
                or re.fullmatch(r"[A-Za-z0-9+/=]+", key)
            ):
                return JSONResponse(
                    err("INVALID_IDEMPOTENCY_KEY", "InvalidIdempotencyKey"),
                    status_code=HTTP_400_BAD_REQUEST,
                )
            redis = request.app.state.redis
            cache_key = f"idem:{request.url.path}:{key}"
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return Response(
                    content=data["body"],
                    status_code=data["status"],
                    media_type="application/json",
                )

            response = await call_next(request)
            body = b"".join([section async for section in response.body_iterator])
            await redis.set(
                cache_key,
                json.dumps({"status": response.status_code, "body": body.decode()}),
                ex=300,
            )
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return await call_next(request)
