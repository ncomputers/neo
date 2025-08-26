from __future__ import annotations

import statistics
import time
from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .routes_preflight import preflight
from .routes_metrics import (
    webhook_attempts_total,
    webhook_failures_total,
)
from .db.tenant import get_engine
from .models_tenant import Order
from .utils.responses import ok

router = APIRouter()

@router.get("/api/admin/ops/summary")
async def admin_ops_summary(request: Request) -> dict:
    """Return uptime and delivery metrics for owners."""
    pf = await preflight()
    uptime = pf.get("status")

    attempts = sum(m._value.get() for m in webhook_attempts_total._metrics.values())
    failures = sum(m._value.get() for m in webhook_failures_total._metrics.values())
    success_rate = (attempts - failures) / attempts if attempts else 1.0

    redis = getattr(request.app.state, "redis", None)
    now = int(time.time())
    open_seconds = 0
    if redis:
        for key in await redis.keys("cb:*:until"):
            until = await redis.get(key)
            if until:
                open_seconds += max(0, int(until) - now)

    tenant = request.headers.get("X-Tenant-ID", "demo")
    engine = get_engine(tenant)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        rows = await session.execute(
            select(Order.accepted_at, Order.ready_at).where(
                Order.accepted_at.isnot(None), Order.ready_at.isnot(None)
            )
        )
        durations = [
            (ready - accepted).total_seconds()
            for accepted, ready in rows.all()
            if accepted and ready
        ]
    await engine.dispose()
    median_prep = statistics.median(durations) if durations else 0.0

    data = {
        "uptime": uptime,
        "webhook_success_rate": success_rate,
        "breaker_open_time": open_seconds,
        "median_kot_prep_time": median_prep,
    }
    return ok(data)
