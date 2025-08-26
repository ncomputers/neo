from __future__ import annotations

import statistics
from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .models_tenant import Order
from .routes_metrics import (
    webhook_attempts_total,
    webhook_failures_total,
    db_replica_healthy,
    kot_delay_alerts_total,
)
from .utils.responses import ok

router = APIRouter()


@router.get("/api/owner/sla")
async def owner_sla(request: Request) -> dict:
    uptime = db_replica_healthy._value.get() * 100.0

    attempts = sum(m._value.get() for m in webhook_attempts_total._metrics.values())
    failures = sum(m._value.get() for m in webhook_failures_total._metrics.values())
    webhook_success = (attempts - failures) / attempts if attempts else 1.0

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

    kot_alerts = kot_delay_alerts_total._value.get()

    data = {
        "uptime_7d": uptime,
        "webhook_success": webhook_success,
        "median_prep": median_prep,
        "kot_delay_alerts": kot_alerts,
    }
    return ok(data)
