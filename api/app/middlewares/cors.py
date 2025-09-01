from __future__ import annotations

from typing import Callable, Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_403_FORBIDDEN

from ..utils.responses import err


class CORSMiddleware(BaseHTTPMiddleware):
    """Simple CORS middleware with origin whitelist and max-age caching."""

    def __init__(
        self,
        app: Callable,
        allowed_origins: Iterable[str] | None = None,
        max_age: int = 3600,
    ) -> None:
        super().__init__(app)
        self.allowed = set(allowed_origins or [])
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        origin = request.headers.get("origin")
        if self.allowed and origin and origin not in self.allowed:
            return JSONResponse(
                err("FORBIDDEN_ORIGIN", "ForbiddenOrigin"),
                status_code=HTTP_403_FORBIDDEN,
                headers={"Vary": "Origin"},
            )
        response = await call_next(request)
        response.headers.setdefault("Vary", "Origin")
        if origin and (not self.allowed or origin in self.allowed):
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
            response.headers.setdefault("Access-Control-Max-Age", str(self.max_age))
        return response
