from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..routes_metrics import idempotency_hits_total, idempotency_conflicts_total


class IdempotencyMetricsMiddleware(BaseHTTPMiddleware):
    """Track idempotency key usage and conflicts."""

    async def dispatch(self, request: Request, call_next):
        has_key = "Idempotency-Key" in request.headers
        response = await call_next(request)
        if has_key:
            idempotency_hits_total.inc()
            if response.status_code == 409:
                idempotency_conflicts_total.inc()

        return response
