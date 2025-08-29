from __future__ import annotations

import os
import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CSPMiddleware(BaseHTTPMiddleware):
    """Attach a nonce-based Content-Security-Policy and related headers."""

    def __init__(
        self,
        app: Callable,
        api_origin: str = "https://API",
        ws_origin: str = "https://WS",
    ) -> None:
        super().__init__(app)
        self.api_origin = api_origin
        self.ws_origin = ws_origin
        self.hsts_enabled = os.getenv("ENABLE_HSTS") == "1"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), notifications=(self)",
        )
        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            f"connect-src 'self' {self.api_origin} {self.ws_origin}; "
            "frame-ancestors 'self'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers.setdefault(
                "Content-Security-Policy-Report-Only", f"{csp}; report-uri /csp/report"
            )
        raw_headers = []
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
        if self.hsts_enabled:
            raw_headers.append(
                (
                    b"strict-transport-security",
                    b"max-age=31536000; includeSubDomains; preload",
                )
            )
        response.raw_headers = raw_headers
        return response
