"""Prometheus middleware for HTTP request metrics."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..routes_metrics import (
    http_requests_total,
    slo_errors_total,
    slo_requests_total,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Increment HTTP request counters."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        http_requests_total.labels(
            path=request.url.path,
            method=request.method,
            status=str(response.status_code),
        ).inc()

        route = request.scope.get("route")
        route_path = route.path if route else request.url.path
        if route_path.startswith("/g/"):
            slo_requests_total.labels(route=route_path).inc()
            if response.status_code >= 500:
                slo_errors_total.labels(route=route_path).inc()
        return response
