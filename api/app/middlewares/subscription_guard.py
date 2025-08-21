"""Middleware to enforce tenant subscription status."""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid

from fastapi import Request
from starlette.responses import JSONResponse

from ..db.master import get_session
from ..models_master import Tenant
from sqlalchemy.exc import StatementError
from ..utils.responses import err


class SubscriptionGuard:
    """Block ordering and billing for expired tenants."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        path = request.url.path
        if request.method == "GET" and "/menu" in path:
            return await call_next(request)

        if (
            request.method == "POST"
            and path.startswith("/g/")
            and ("order" in path or "bill" in path)
        ):
            tenant_id = request.headers.get("X-Tenant-ID")
            tenant = None
            if tenant_id:
                lookup_id = tenant_id
                try:
                    lookup_id = uuid.UUID(tenant_id)
                except ValueError:
                    pass
                async with get_session() as session:
                    try:
                        tenant = await session.get(Tenant, tenant_id)
                    except StatementError:

                        tenant = None
                if tenant and tenant.subscription_expires_at:
                    grace = tenant.grace_period_days or 7
                    if datetime.utcnow() > tenant.subscription_expires_at + timedelta(
                        days=grace
                    ):
                        return JSONResponse(
                            err("SUB_403", "SubscriptionExpired"), status_code=403
                        )
        return await call_next(request)
