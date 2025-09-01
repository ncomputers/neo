from __future__ import annotations

import os
import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response


class CSPMiddleware(BaseHTTPMiddleware):
    """Attach a nonce-based Content-Security-Policy header."""

    def __init__(
        self,
        app: Callable,
        api_base: str | None = None,
        ws_base: str | None = None,
    ) -> None:
        super().__init__(app)
        self.api_base = api_base or os.getenv("API_BASE", "https://API")
        self.ws_base = ws_base or os.getenv("WS_BASE", "https://WS")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            f"connect-src 'self' {self.api_base} {self.ws_base}; "
            "frame-ancestors 'self'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        if response.headers.get("content-type", "").startswith("text/html"):
            body = b"".join([chunk async for chunk in response.body_iterator])
            content = body.decode("utf-8").replace("{{ csp_nonce }}", nonce)
            response = HTMLResponse(
                content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        return response
