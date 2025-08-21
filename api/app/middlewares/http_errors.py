from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..routes_metrics import http_errors_total


class HttpErrorCounterMiddleware(BaseHTTPMiddleware):
    """Increment counter for HTTP error responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if 400 <= response.status_code < 600:
            http_errors_total.labels(status=str(response.status_code)).inc()
        return response
