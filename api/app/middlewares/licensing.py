from __future__ import annotations

"""Middleware to enforce tenant licensing constraints."""

from datetime import datetime
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..db.master import get_session
from ..models_master import Tenant
from ..utils.responses import err

PLAN_FEATURES: Dict[str, Dict[str, bool]] = {
    "starter": {
        "hotel_mode": False,
        "counter_mode": True,
        "exports": False,
        "coupons": False,
        "dashboard_charts": False,
    },
    "pro": {
        "hotel_mode": True,
        "counter_mode": True,
        "exports": True,
        "coupons": True,
        "dashboard_charts": True,
    },
}


class LicensingMiddleware(BaseHTTPMiddleware):
    """Validate tenant plan and feature access."""

    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")
        tenant = None
        if tenant_id:
            try:
                async with get_session() as session:
                    tenant = await session.get(Tenant, tenant_id)
            except Exception:  # pragma: no cover - DB errors fall through
                tenant = None

        if tenant:
            plan = getattr(tenant, "plan", "starter")
            now = datetime.utcnow()
            status = getattr(tenant, "status", "active")
            grace_until = getattr(tenant, "grace_until", None)
            if status == "expired" and grace_until and now > grace_until:
                return JSONResponse(
                    err("LICENSE_EXPIRED", "License expired"), status_code=402
                )

            feature = None
            path = request.url.path
            if "/exports" in path:
                feature = "exports"
            elif path.startswith("/h/"):
                feature = "hotel_mode"
            elif path.startswith("/c/"):
                feature = "counter_mode"
            elif "/coupons" in path:
                feature = "coupons"
            elif "/dashboard/charts" in path:
                feature = "dashboard_charts"

            if feature and not PLAN_FEATURES.get(plan, {}).get(feature, False):
                return JSONResponse(
                    err("FEATURE_NOT_IN_PLAN", "Feature not in plan"),
                    status_code=403,
                )

            response = await call_next(request)
            response.headers["X-Tenant-Plan"] = plan
            return response

        return await call_next(request)
