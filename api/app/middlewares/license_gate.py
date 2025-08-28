"""Subscription enforcement middleware with caching and decorators."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Callable, Awaitable

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


def license_required(allow_in_grace: bool = True) -> Depends:
    async def checker(request: Request):
        status = getattr(request.state, "license_status", "ACTIVE")
        if status == "EXPIRED" or (status == "GRACE" and not allow_in_grace):
            from ..routes_metrics import blocked_actions_total

            blocked_actions_total.labels(route=request.url.path).inc()
            raise HTTPException(
                status_code=402,
                detail={"code": "SUBSCRIPTION_EXPIRED", "renew_url": "/admin/billing"},
            )
    return Depends(checker)


def billing_always_allowed(func: Callable) -> Callable:
    return func


class LicenseGate(BaseHTTPMiddleware):
    """Attach license status to request and cache for 60s."""

    def __init__(self, app, ttl: int = 60):
        super().__init__(app)
        self.ttl = ttl

    async def _status_from_cache(self, redis: Redis, key: str) -> tuple[str, int | None] | None:
        cached = await redis.get(key)
        if not cached:
            return None
        try:
            data = json.loads(cached)
            return data.get("status", "ACTIVE"), data.get("days_left")
        except Exception:  # pragma: no cover
            return None

    async def _compute_status(self, tenant: dict[str, Any] | None) -> tuple[str, int | None]:
        status = "ACTIVE"
        days_left: int | None = None
        if not tenant:
            return status, days_left
        now = datetime.utcnow()
        expiry = tenant.get("subscription_expires_at")
        grace_days = tenant.get("grace_period_days", 0)
        if not expiry:
            return status, days_left
        if now > expiry + timedelta(days=grace_days):
            status = "EXPIRED"
            days_left = 0
        elif now > expiry:
            status = "GRACE"
            days_left = (expiry + timedelta(days=grace_days) - now).days
        else:
            status = "ACTIVE"
            days_left = (expiry - now).days
        return status, days_left

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        tenant_id = request.headers.get("X-Tenant-ID")
        redis: Redis | None = getattr(request.app.state, "redis", None)
        status = "ACTIVE"
        days_left: int | None = None
        cache_key = f"license:{tenant_id}" if tenant_id else None
        if tenant_id and redis and cache_key:
            cached = await self._status_from_cache(redis, cache_key)
            if cached:
                status, days_left = cached
        if days_left is None:
            from ..main import TENANTS  # inline import

            tenant = TENANTS.get(tenant_id) if tenant_id else None
            status, days_left = await self._compute_status(tenant)
            if tenant_id and redis and cache_key:
                await redis.set(
                    cache_key,
                    json.dumps({"status": status, "days_left": days_left}),
                    ex=self.ttl,
                )

        request.state.license_status = status
        request.state.license_days_left = days_left

        try:  # metrics
            from ..routes_metrics import license_status_gauge

            license_status_gauge.labels(tenant=tenant_id or "", status=status).set(1)
        except Exception:
            pass

        return await call_next(request)


__all__ = ["LicenseGate", "license_required", "billing_always_allowed"]
