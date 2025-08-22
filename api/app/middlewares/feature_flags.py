"""Middleware to guard hotel and counter features per tenant."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN

from ..db.master import get_session
from ..models_master import Tenant
from ..utils.responses import err


class FeatureFlagsMiddleware(BaseHTTPMiddleware):
    """Gate requests to feature-specific routes based on tenant flags."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/h/") or path.startswith("/c/"):
            tenant_id = request.headers.get("X-Tenant-ID")
            if tenant_id:
                async with get_session() as session:
                    tenant = await session.get(Tenant, tenant_id)
                if tenant:
                    if path.startswith("/h/") and not getattr(tenant, "enable_hotel", False):
                        return JSONResponse(
                            err("FEATURE_OFF", "Hotel mode disabled"),
                            status_code=HTTP_403_FORBIDDEN,
                        )
                    if path.startswith("/c/") and not getattr(
                        tenant, "enable_counter", False
                    ):
                        return JSONResponse(
                            err("FEATURE_OFF", "Counter mode disabled"),
                            status_code=HTTP_403_FORBIDDEN,
                        )
        return await call_next(request)
