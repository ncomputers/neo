from __future__ import annotations

from typing import Callable, Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_403_FORBIDDEN


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware allowing only whitelisted origins."""

    def __init__(
        self,
        app: Callable,
        allowed_origins: Iterable[str] | None = None,
        max_age: int = 3600,
    ) -> None:
        super().__init__(app)
        self.allowed = {o for o in (allowed_origins or []) if o}
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        origin = request.headers.get("origin")
        if origin and self.allowed and origin not in self.allowed:
            return Response(status_code=HTTP_403_FORBIDDEN, headers={"Vary": "Origin"})

        # Handle preflight
        if (
            request.method == "OPTIONS"
            and origin
            and (not self.allowed or origin in self.allowed)
            and request.headers.get("access-control-request-method")
        ):
            headers = {
                "Access-Control-Allow-Origin": origin,
                "Vary": "Origin",
                "Access-Control-Allow-Methods": request.headers.get(
                    "access-control-request-method", ""
                ),
                "Access-Control-Allow-Headers": request.headers.get(
                    "access-control-request-headers", ""
                ),
                "Access-Control-Max-Age": str(self.max_age),
                "Access-Control-Allow-Credentials": "true",
            }
            return Response(status_code=200, headers=headers)

        response = await call_next(request)
        response.headers.setdefault("Vary", "Origin")
        if origin and (not self.allowed or origin in self.allowed):
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")
            response.headers.setdefault("Access-Control-Max-Age", str(self.max_age))
        return response
