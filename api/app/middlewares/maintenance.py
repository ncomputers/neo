"""Maintenance mode middleware."""

from __future__ import annotations

import os
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..db.master import get_session
from ..models_master import Tenant


class MaintenanceMiddleware(BaseHTTPMiddleware):
    """Block requests during global or per-tenant maintenance windows."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path.startswith("/admin") or path.startswith("/api/admin"):
            return await call_next(request)

        if os.getenv("MAINTENANCE") == "1":
            return JSONResponse({"code": "MAINTENANCE"}, status_code=503)

        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            try:
                async with get_session() as session:
                    tenant = await session.get(Tenant, tenant_id)
            except Exception:  # pragma: no cover - DB errors fall through
                tenant = None

            if tenant:
                closed_at = getattr(tenant, "closed_at", None)
                if closed_at:
                    return JSONResponse({"code": "TENANT_CLOSED"}, status_code=403)
                maintenance_until = getattr(tenant, "maintenance_until", None)
                if maintenance_until and datetime.utcnow() < maintenance_until:
                    retry = int((maintenance_until - datetime.utcnow()).total_seconds())
                    resp = JSONResponse({"code": "MAINTENANCE"}, status_code=503)
                    resp.headers["Retry-After"] = str(retry)
                    return resp

        return await call_next(request)
