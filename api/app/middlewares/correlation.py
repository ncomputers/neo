import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from opentelemetry import trace


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a correlation ID."""

    async def dispatch(self, request: Request, call_next: Callable):
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        trace.get_current_span().set_attribute("request_id", correlation_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        return response
