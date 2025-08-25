from __future__ import annotations

import os
import re
import secrets
from typing import List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
)

from ..utils.responses import err
from .guest_utils import _is_guest_post


class SecurityMiddleware(BaseHTTPMiddleware):
    """Basic hardening for guest endpoints and CORS."""

    def __init__(self, app) -> None:
        super().__init__(app)
        allowed = os.getenv("ALLOWED_ORIGINS", "*")
        if allowed == "*":
            self.allowed_origins: List[str] = ["*"]
        else:
            self.allowed_origins = [o.strip() for o in allowed.split(",") if o.strip()]
        self.max_bytes = 256 * 1024
        self.key_pattern = re.compile(r"^[A-Za-z0-9_\-=:]+$")
        self.hsts_enabled = os.getenv("ENABLE_HSTS") == "1"

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if (
            self.allowed_origins != ["*"]
            and origin
            and origin not in self.allowed_origins
        ):
            return JSONResponse(
                err("FORBIDDEN_ORIGIN", "ForbiddenOrigin"),
                status_code=HTTP_403_FORBIDDEN,
            )

        if _is_guest_post(request.url.path, request.method):
            body = await request.body()
            if len(body) > self.max_bytes:
                return JSONResponse(
                    err("BODY_TOO_LARGE", "BodyTooLarge"),
                    status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            key = request.headers.get("Idempotency-Key")
            if key and (len(key) > 128 or not self.key_pattern.fullmatch(key)):
                return JSONResponse(
                    err("BAD_IDEMPOTENCY_KEY", "BadIdempotencyKey"),
                    status_code=HTTP_400_BAD_REQUEST,
                )

            async def receive() -> dict:
                return {"type": "http.request", "body": body}

            request._receive = receive

        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        if origin:
            if self.allowed_origins == ["*"]:
                response.headers.setdefault("access-control-allow-origin", "*")
            elif origin in self.allowed_origins:
                response.headers.setdefault("access-control-allow-origin", origin)
                response.headers.setdefault("vary", "Origin")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            f"style-src 'self' 'nonce-{nonce}'; "
            f"script-src 'self' 'nonce-{nonce}'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        if self.hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
