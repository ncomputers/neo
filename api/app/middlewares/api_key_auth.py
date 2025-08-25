from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..db.tenant import get_tenant_session
from ..models_tenant import ApiKey
from ..utils.responses import err


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests to reporting endpoints using bearer API keys."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if "/reports/" in path:
            tenant_id = self._extract_tenant(path)
            if tenant_id:
                auth = request.headers.get("Authorization")
                if not auth or not auth.startswith("Bearer "):
                    return JSONResponse(
                        err("API_KEY_MISSING", "Missing API key"), status_code=401
                    )
                token = auth.split(" ", 1)[1]
                async with get_tenant_session(tenant_id) as session:
                    result = await session.execute(
                        select(ApiKey).where(ApiKey.token == token)
                    )
                    key = result.scalar_one_or_none()
                if key is None or "read:reports" not in key.scopes:
                    return JSONResponse(
                        err("API_KEY_INVALID", "Invalid API key"), status_code=403
                    )
        return await call_next(request)

    @staticmethod
    def _extract_tenant(path: str) -> Optional[str]:
        parts = path.split("/")
        try:
            idx = parts.index("outlet")
            return parts[idx + 1]
        except (ValueError, IndexError):
            return None
