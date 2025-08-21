"""Prometheus middleware for HTTP request metrics."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..metrics import http_requests_total


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Increment HTTP request counters."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        http_requests_total.labels(
            path=request.url.path,
            method=request.method,
            status=str(response.status_code),
        ).inc()
        return response
