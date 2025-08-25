from __future__ import annotations

"""Middleware to enforce tenant licensing constraints."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..db.master import get_session
from ..db.tenant import get_engine
from ..models_master import Tenant
from ..models_tenant import MenuItem, Table
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


async def _table_count(tenant_id: str) -> int:
    """Return active table count for ``tenant_id``."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            stmt = (
                select(func.count())
                .select_from(Table)
                .where(Table.deleted_at.is_(None))
            )
            return await session.scalar(stmt) or 0
    finally:  # pragma: no cover - defensive
        await engine.dispose()


async def _menu_item_count(tenant_id: str) -> int:
    """Return active menu item count for ``tenant_id``."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            stmt = (
                select(func.count())
                .select_from(MenuItem)
                .where(MenuItem.deleted_at.is_(None))
            )
            return await session.scalar(stmt) or 0
    finally:  # pragma: no cover - defensive
        await engine.dispose()


def storage_bytes(tenant_id: str) -> int:
    """Return total stored media bytes for ``tenant_id``."""

    base = Path(os.getenv("MEDIA_DIR", "media")) / tenant_id
    if not base.exists():
        return 0
    return sum(p.stat().st_size for p in base.rglob("*") if p.is_file())


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
            request.state.tenant = tenant
            plan = getattr(tenant, "plan", "starter")
            now = datetime.utcnow()
            status = getattr(tenant, "status", "active")
            grace_until = getattr(tenant, "grace_until", None)
            if status == "expired" and grace_until and now > grace_until:
                return JSONResponse(
                    err("LICENSE_EXPIRED", "License expired"), status_code=402
                )

            limits = getattr(tenant, "license_limits", {}) or {}
            path = request.url.path
            method = request.method
            feature = None
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

            if method == "POST" and path.endswith("/tables"):
                limit = limits.get("max_tables")
                if limit is not None and await _table_count(tenant_id) >= limit:
                    return JSONResponse(
                        err("FEATURE_LIMIT", "table limit reached"), status_code=403
                    )
            elif method == "POST" and "/menu/items" in path:
                limit = limits.get("max_menu_items")
                if limit is not None and await _menu_item_count(tenant_id) >= limit:
                    return JSONResponse(
                        err("FEATURE_LIMIT", "menu item limit reached"),
                        status_code=403,
                    )
            if "/exports" in path:
                limit = limits.get("max_daily_exports")
                redis = getattr(request.app.state, "redis", None)
                if limit is not None and redis is not None:
                    key = f"usage:{tenant_id}:exports:{datetime.utcnow():%Y%m%d}"
                    count = int(await redis.get(key) or 0)
                    if count >= limit:
                        return JSONResponse(
                            err("FEATURE_LIMIT", "daily export limit reached"),
                            status_code=403,
                        )
                    response = await call_next(request)
                    if response.status_code < 400:
                        await redis.incr(key)
                    response.headers["X-Tenant-Plan"] = plan
                    return response

            response = await call_next(request)
            response.headers["X-Tenant-Plan"] = plan
            return response

        return await call_next(request)
