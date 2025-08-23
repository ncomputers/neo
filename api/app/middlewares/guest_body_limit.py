from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE

from ..utils.responses import err
from .guest_utils import _is_guest_post


class GuestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject guest POST bodies exceeding a fixed size."""

    def __init__(self, app, max_kb: int = 256) -> None:
        super().__init__(app)
        self.max_bytes = max_kb * 1024

    async def dispatch(self, request: Request, call_next):
        if _is_guest_post(request.url.path, request.method):
            body = await request.body()
            if len(body) > self.max_bytes:
                return JSONResponse(
                    err("PAYLOAD_TOO_LARGE", "PayloadTooLarge"),
                    status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            async def receive() -> dict:
                return {"type": "http.request", "body": body}

            request._receive = receive
        return await call_next(request)
