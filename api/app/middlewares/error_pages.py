from __future__ import annotations

"""Serve static HTML error pages when requested."""

from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse


class HTMLErrorPagesMiddleware(BaseHTTPMiddleware):
    """Return static HTML pages for common errors when ``Accept: text/html``."""

    def __init__(self, app, static_dir: Path):
        super().__init__(app)
        self.static_dir = static_dir

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        accept = request.headers.get("accept", "")
        if "text/html" in accept and response.status_code in {401, 403, 404, 500}:
            error_file = self.static_dir / "errors" / f"{response.status_code}.html"
            if error_file.is_file():
                return FileResponse(error_file, status_code=response.status_code)
        return response
