from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_413_REQUEST_ENTITY_TOO_LARGE

from ..utils.responses import err
from .guest_utils import _is_guest_post


class SecurityMiddleware(BaseHTTPMiddleware):
    """Basic hardening for guest endpoints."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.max_bytes = 256 * 1024

    async def dispatch(self, request: Request, call_next):
        if _is_guest_post(request.url.path, request.method):
            body = await request.body()
            if len(body) > self.max_bytes:
                return JSONResponse(
                    err("BODY_TOO_LARGE", "BodyTooLarge"),
                    status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            key = request.headers.get("Idempotency-Key")
            if key:
                try:
                    uuid.UUID(key)
                except ValueError:
                    return JSONResponse(
                        err("BAD_IDEMPOTENCY_KEY", "BadIdempotencyKey"),
                        status_code=HTTP_400_BAD_REQUEST,
                    )

            async def receive() -> dict:
                return {"type": "http.request", "body": body}

            request._receive = receive

        return await call_next(request)
