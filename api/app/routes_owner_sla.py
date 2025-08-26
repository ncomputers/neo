from __future__ import annotations

import statistics
import datetime
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
    history = getattr(request.app.state, "owner_sla_history", {})

    # Uptime is a gauge representing the last check. Previous 7-day uptime
    # is supplied via app state for trend calculation.
    uptime = db_replica_healthy._value.get() * 100.0
    prev_uptime = history.get("uptime_prev", uptime)

    # Webhook attempts/failures are monotonic counters. Snapshots from 7 and
    # 14 days ago are provided via app state to compute window deltas.
    attempts_total = sum(m._value.get() for m in webhook_attempts_total._metrics.values())
    failures_total = sum(m._value.get() for m in webhook_failures_total._metrics.values())
    attempts_7d = history.get("webhook_attempts_7d", 0)
    failures_7d = history.get("webhook_failures_7d", 0)
    attempts_14d = history.get("webhook_attempts_14d", 0)
    failures_14d = history.get("webhook_failures_14d", 0)

    curr_attempts = attempts_total - attempts_7d
    curr_failures = failures_total - failures_7d
    prev_attempts = attempts_7d - attempts_14d
    prev_failures = failures_7d - failures_14d

    webhook_success = (
        (curr_attempts - curr_failures) / curr_attempts if curr_attempts else 1.0
    )
    prev_webhook_success = (
        (prev_attempts - prev_failures) / prev_attempts if prev_attempts else 1.0
    )

    tenant = request.headers.get("X-Tenant-ID", "demo")
    engine = get_engine(tenant)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        now = datetime.datetime.utcnow()
        start_curr = now - datetime.timedelta(days=7)
        start_prev = now - datetime.timedelta(days=14)
        rows = await session.execute(
            select(Order.accepted_at, Order.ready_at).where(
                Order.accepted_at >= start_prev, Order.ready_at.isnot(None)
            )
        )
        curr_durations: list[float] = []
        prev_durations: list[float] = []
        for accepted, ready in rows.all():
            if accepted and ready:
                secs = (ready - accepted).total_seconds()
                if accepted >= start_curr:
                    curr_durations.append(secs)
                else:
                    prev_durations.append(secs)
    await engine.dispose()
    median_prep = statistics.median(curr_durations) if curr_durations else 0.0
    prev_median_prep = statistics.median(prev_durations) if prev_durations else 0.0

    kot_total = kot_delay_alerts_total._value.get()
    kot_7d = history.get("kot_delay_alerts_7d", 0)
    kot_14d = history.get("kot_delay_alerts_14d", 0)
    kot_curr = kot_total - kot_7d
    kot_prev = kot_7d - kot_14d

    data = {
        "uptime_7d": uptime,
        "uptime_trend": uptime - prev_uptime,
        "webhook_success": webhook_success,
        "webhook_success_trend": webhook_success - prev_webhook_success,
        "median_prep": median_prep,
        "median_prep_trend": median_prep - prev_median_prep,
        "kot_delay_alerts": kot_curr,
        "kot_delay_alerts_trend": kot_curr - kot_prev,
    }
    return ok(data)
