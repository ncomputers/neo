from __future__ import annotations

import os
import secrets
import uuid
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
        allowed = os.getenv("ALLOWED_ORIGINS", "")
        self.allowed_origins: List[str] = [
            o.strip() for o in allowed.split(",") if o.strip()
        ]
        self.max_bytes = 256 * 1024
        self.hsts_enabled = os.getenv("ENABLE_HSTS") == "1"

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if self.allowed_origins and origin and origin not in self.allowed_origins:
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

        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        if origin and origin in self.allowed_origins:
            response.headers.setdefault("access-control-allow-origin", origin)
            response.headers.setdefault("vary", "Origin")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            f"style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            f"script-src 'self' 'nonce-{nonce}'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        raw_headers: list[tuple[bytes, bytes]] = []
        for name, value in response.raw_headers:
            if name.lower() == b"set-cookie":
                cookie = value.decode("latin1")
                lower = cookie.lower()
                if "httponly" not in lower:
                    cookie += "; HttpOnly"
                if "secure" not in lower:
                    cookie += "; Secure"
                if "samesite" not in lower:
                    cookie += "; SameSite=Lax"
                raw_headers.append((name, cookie.encode("latin1")))
            else:
                raw_headers.append((name, value))
        response.raw_headers = raw_headers

        if self.hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
