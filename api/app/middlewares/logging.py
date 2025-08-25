import json
import logging
import os
import random
import time
import uuid
from contextvars import ContextVar
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..utils.responses import err
from .guest_utils import _is_guest_post

PII_KEYS = {"pin", "utr", "auth", "gstin"}
LOG_SAMPLE_GUEST_4XX = float(os.getenv("LOG_SAMPLE_GUEST_4XX", "0.1"))


request_id_ctx = ContextVar("request_id", default=None)
logger = logging.getLogger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Emit structured inbound/outbound request logs with a request ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        body_bytes = await request.body()

        async def receive() -> dict:
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request._receive = receive

        body = None
        if body_bytes:
            try:
                body = json.loads(body_bytes)
            except Exception:
                pass

        query = dict(request.query_params)

        def _redact(obj):
            if isinstance(obj, dict):
                return {
                    k: ("***" if k.lower() in PII_KEYS else _redact(v))
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [_redact(v) for v in obj]
            return obj

        inbound = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "tenant": request.headers.get("X-Tenant"),
            "path": request.url.path,
            "method": request.method,
            "ip": request.client.host if request.client else None,
            "ua": request.headers.get("user-agent"),
        }
        if query:
            inbound["query"] = _redact(query)
        if body is not None:
            inbound["body"] = _redact(body)

        start = time.perf_counter()
        response = None
        error_id = None
        try:
            response = await call_next(request)
        except Exception:
            error_id = str(uuid.uuid4())
            logger.exception(
                json.dumps({"request_id": request_id, "error_id": error_id})
            )
            payload = err(500, "Internal Server Error")
            payload["error_id"] = error_id
            response = JSONResponse(payload, status_code=500)
        dur_ms = int((time.perf_counter() - start) * 1000)
        status = response.status_code if response else 500
        outbound = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "status": status,
            "dur_ms": dur_ms,
        }
        if error_id:
            outbound["error_id"] = error_id

        should_log = True
        if _is_guest_post(request.url.path, request.method) and 400 <= status < 500:
            if random.random() >= LOG_SAMPLE_GUEST_4XX:
                should_log = False

        if should_log:
            logger.info(json.dumps(inbound))
            logger.info(json.dumps(outbound))

        request_id_ctx.reset(token)
        return response
