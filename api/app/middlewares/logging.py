import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


request_id_ctx = ContextVar("request_id", default=None)
logger = logging.getLogger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Emit structured inbound/outbound request logs with a request ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        inbound = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "tenant": request.headers.get("X-Tenant"),
            "path": request.url.path,
            "method": request.method,
            "ip": request.client.host if request.client else None,
            "ua": request.headers.get("user-agent"),
        }
        logger.info(json.dumps(inbound))

        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            dur_ms = int((time.perf_counter() - start) * 1000)
            outbound = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id,
                "status": response.status_code if response else 500,
                "dur_ms": dur_ms,
            }
            logger.info(json.dumps(outbound))
            request_id_ctx.reset(token)
