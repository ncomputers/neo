"""Prometheus middleware for HTTP request metrics."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..routes_metrics import http_requests_total, slo_errors_total, slo_requests_total
from ..slo import slo_tracker



class PrometheusMiddleware(BaseHTTPMiddleware):
    """Increment HTTP request counters."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        status = response.status_code
        http_requests_total.labels(
            path=path,
            method=request.method,
            status=str(status),
        ).inc()
        slo_requests_total.labels(route=path).inc()
        error = status >= 500
        if error:
            slo_errors_total.labels(route=path).inc()
        slo_tracker.record(path, error=error)

        return response
