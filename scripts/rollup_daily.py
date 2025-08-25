#!/usr/bin/env python3
"""Recompute daily sales rollups.

Aggregates orders, sales, tax, tip and payment mix for a given tenant and
stores them in the ``sales_rollup`` table. Intended to run hourly to refresh
yesterday and today's rows."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.tenant import get_engine as get_tenant_engine  # type: ignore  # noqa: E402
from app.models_tenant import (  # type: ignore  # noqa: E402
    Invoice,
    Order,
    Payment,
    SalesRollup,
)

from api.app.routes_metrics import (  # type: ignore  # noqa: E402
    rollup_failures_total,
    rollup_runs_total,
)

try:  # Optional Redis client for idempotency lock
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover - redis not installed
    redis = None  # type: ignore


async def rollup_day(session: AsyncSession, tenant: str, day: date, tz: str) -> None:
    """Compute and store rollup for ``tenant`` on ``day``."""
    tzinfo = ZoneInfo(tz)
    start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
    end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

    orders = await session.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.placed_at >= start, Order.placed_at <= end)
    )
    orders = int(orders or 0)

    sales = await session.scalar(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.created_at >= start, Invoice.created_at <= end
        )
    )
    sales = float(sales or 0)

    tax = 0.0
    tip = 0.0
    result = await session.execute(
        select(Invoice.gst_breakup, Invoice.tip).where(
            Invoice.created_at >= start, Invoice.created_at <= end
        )
    )
    for gst, tp in result.all():
        if gst:
            tax += sum(float(v) for v in gst.values())
        tip += float(tp or 0)

    result = await session.execute(
        select(Payment.mode, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.created_at >= start, Payment.created_at <= end)
        .group_by(Payment.mode)
    )
    modes = {mode: float(amt or 0) for mode, amt in result.all()}

    existing = await session.get(SalesRollup, {"tenant_id": tenant, "d": day})
    if existing:
        existing.orders = orders
        existing.sales = sales
        existing.tax = tax
        existing.tip = tip
        existing.modes_json = modes
    else:
        session.add(
            SalesRollup(
                tenant_id=tenant,
                d=day,
                orders=orders,
                sales=sales,
                tax=tax,
                tip=tip,
                modes_json=modes,
            )
        )
    await session.commit()


async def main(tenant: str) -> None:
    tz = os.getenv("DEFAULT_TZ", "UTC")
    today = datetime.now(ZoneInfo(tz)).date()
    days = [today - timedelta(days=1), today]

    engine = get_tenant_engine(tenant)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    redis_url = os.getenv("REDIS_URL")
    redis_client = redis.from_url(redis_url) if redis and redis_url else None
    try:
        async with sessionmaker() as session:
            for day in days:
                key = f"rollup:{tenant}:{day.isoformat()}"
                if redis_client:
                    acquired = await redis_client.set(key, "1", ex=3600, nx=True)
                    if not acquired:
                        continue
                try:
                    await rollup_day(session, tenant, day, tz)
                    rollup_runs_total.inc()
                except Exception:
                    rollup_failures_total.inc()
                    if redis_client:
                        await redis_client.delete(key)
                    raise
    finally:
        await engine.dispose()
        if redis_client:
            await redis_client.close()


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Recompute daily sales rollups")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(main(args.tenant))


if __name__ == "__main__":
    _cli()
