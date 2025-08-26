"""Owner multi-outlet analytics summary routes."""

from __future__ import annotations

import csv
import statistics
from contextlib import asynccontextmanager
from datetime import datetime, time, timezone
from io import StringIO
from typing import Iterable
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.replica import read_only, replica_session
from .db.tenant import get_engine
from .models_master import Tenant
from .models_tenant import Invoice, Order, OrderItem, OrderStatus

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


async def _get_tenants_info(tenant_ids: Iterable[str]) -> dict[str, dict]:
    async with replica_session() as session:
        result = await session.execute(
            select(Tenant.id, Tenant.name, Tenant.timezone).where(
                Tenant.id.in_(tenant_ids)
            )
        )
        rows = result.all()
    info: dict[str, dict] = {}
    for tid, name, tz in rows:
        info[tid] = {"name": name, "tz": tz or "UTC"}
    return info


def _parse_scope(request: Request) -> list[str]:
    header = request.headers.get("x-tenant-ids")
    if not header:
        raise HTTPException(status_code=403, detail="forbidden")
    return [h.strip() for h in header.split(",") if h.strip()]


@router.get("/api/analytics/outlets")
@read_only
async def analytics_outlets(
    request: Request,
    ids: str,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    format: str | None = None,
):
    tenant_scope = set(_parse_scope(request))
    requested = [tid.strip() for tid in ids.split(",") if tid.strip()]
    if not requested:
        raise HTTPException(status_code=400, detail="ids required")
    if not set(requested).issubset(tenant_scope):
        raise HTTPException(status_code=403, detail="forbidden")

    start_date = datetime.strptime(from_, "%Y-%m-%d").date()
    end_date = datetime.strptime(to, "%Y-%m-%d").date()
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="invalid range")

    info = await _get_tenants_info(requested)
    total_orders = 0
    total_sales = 0.0
    total_cancelled = 0
    top: dict[str, int] = {}
    durations: list[float] = []
    per_outlet: list[dict] = []

    for tid in requested:
        tz = info.get(tid, {}).get("tz", "UTC")
        tzinfo = ZoneInfo(tz)
        start_dt = datetime.combine(start_date, time.min, tzinfo).astimezone(
            timezone.utc
        )
        end_dt = datetime.combine(end_date, time.max, tzinfo).astimezone(timezone.utc)
        async with _session(tid) as session:
            orders = await session.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.placed_at >= start_dt, Order.placed_at <= end_dt)
            )
            cancelled = await session.scalar(
                select(func.count())
                .select_from(Order)
                .where(
                    Order.placed_at >= start_dt,
                    Order.placed_at <= end_dt,
                    Order.status == OrderStatus.CANCELLED,
                )
            )
            sales = await session.scalar(
                select(func.coalesce(func.sum(Invoice.total), 0)).where(
                    Invoice.created_at >= start_dt, Invoice.created_at <= end_dt
                )
            )
            result = await session.execute(
                select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("qty"))
                .join(Order, Order.id == OrderItem.order_id)
                .where(Order.placed_at >= start_dt, Order.placed_at <= end_dt)
                .group_by(OrderItem.name_snapshot)
                .order_by(desc("qty"))
                .limit(5)
            )
            items = [(n, int(q)) for n, q in result.all()]
            rows = await session.execute(
                select(Order.accepted_at, Order.ready_at).where(
                    Order.accepted_at.is_not(None),
                    Order.ready_at.is_not(None),
                    Order.accepted_at >= start_dt,
                    Order.ready_at <= end_dt,
                )
            )
            durs = [
                (ready - accepted).total_seconds()
                for accepted, ready in rows.all()
                if accepted and ready
            ]

        o = int(orders or 0)
        c = int(cancelled or 0)
        s = float(sales or 0.0)
        total_orders += o
        total_sales += s
        total_cancelled += c
        for name, qty in items:
            top[name] = top.get(name, 0) + qty
        durations.extend(durs)
        per_outlet.append(
            {
                "id": tid,
                "orders": o,
                "sales": s,
                "aov": float(s / o) if o else 0.0,
                "median_prep": statistics.median(durs) if durs else 0.0,
                "voids_pct": float(c / o * 100) if o else 0.0,
            }
        )

    aov = float(total_sales / total_orders) if total_orders else 0.0
    top_items = sorted(top.items(), key=lambda x: x[1], reverse=True)[:5]
    median_prep = statistics.median(durations) if durations else 0.0
    voids_pct = float(total_cancelled / total_orders * 100) if total_orders else 0.0
    data = {
        "orders": total_orders,
        "sales": total_sales,
        "aov": aov,
        "top_items": [{"name": n, "qty": q} for n, q in top_items],
        "median_prep": median_prep,
        "voids_pct": voids_pct,
    }

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["outlet_id", "orders", "sales", "aov", "median_prep", "voids_pct"]
        )
        for row in per_outlet:
            writer.writerow(
                [
                    row["id"],
                    row["orders"],
                    f"{row['sales']:.2f}",
                    f"{row['aov']:.2f}",
                    f"{row['median_prep']:.2f}",
                    f"{row['voids_pct']:.2f}",
                ]
            )
        resp = Response(content=output.getvalue(), media_type="text/csv")
        resp.headers["Content-Disposition"] = "attachment; filename=outlets.csv"
        return resp

    return data
