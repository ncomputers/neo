import uuid
import logging
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context variable used by log filter to inject request id
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("api")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensure every request carries a request id."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        request.state.request_id = req_id
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = req_id
        return response
