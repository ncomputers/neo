"""Owner multi-outlet aggregate routes."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, time, timezone
from io import StringIO
from zoneinfo import ZoneInfo
import csv
import statistics
from typing import Iterable

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.replica import read_only, replica_session
from .db.tenant import get_engine
from .models_master import Tenant
from .models_tenant import Invoice, Order, OrderItem
from .pdf.render import render_template
from .repos_sqlalchemy import dashboard_repo_sql, invoices_repo_sql

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
    top: dict[str, int] = {}
    durations: list[float] = []
    per_outlet: list[dict] = []

    for tid in requested:
        tz = info.get(tid, {}).get("tz", "UTC")
        tzinfo = ZoneInfo(tz)
        start_dt = datetime.combine(start_date, time.min, tzinfo).astimezone(timezone.utc)
        end_dt = datetime.combine(end_date, time.max, tzinfo).astimezone(timezone.utc)
        async with _session(tid) as session:
            orders = await session.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.placed_at >= start_dt, Order.placed_at <= end_dt)
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
        s = float(sales or 0.0)
        total_orders += o
        total_sales += s
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
            }
        )

    aov = float(total_sales / total_orders) if total_orders else 0.0
    top_items = sorted(top.items(), key=lambda x: x[1], reverse=True)[:5]
    median_prep = statistics.median(durations) if durations else 0.0
    data = {
        "orders": total_orders,
        "sales": total_sales,
        "aov": aov,
        "top_items": [{"name": n, "qty": q} for n, q in top_items],
        "median_prep": median_prep,
    }

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["outlet_id", "orders", "sales", "aov", "median_prep"])
        for row in per_outlet:
            writer.writerow(
                [
                    row["id"],
                    row["orders"],
                    f"{row['sales']:.2f}",
                    f"{row['aov']:.2f}",
                    f"{row['median_prep']:.2f}",
                ]
            )
        resp = Response(content=output.getvalue(), media_type="text/csv")
        resp.headers["Content-Disposition"] = "attachment; filename=outlets.csv"
        return resp

    return data

@router.get("/api/owner/{owner_id}/dashboard/charts")
@read_only
async def owner_dashboard_charts(owner_id: str, request: Request, range: int = 7):
    if range not in (7, 30, 90):
        raise HTTPException(status_code=400, detail="invalid range")
    tenant_ids = _parse_scope(request)
    redis = request.app.state.redis
    cache_key = f"owner:charts:{owner_id}:{range}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    today = datetime.utcnow().date()
    start = today - timedelta(days=range - 1)

    agg_sales: dict[str, float] = {}
    agg_orders: dict[str, int] = {}
    modes = {"cash": 0.0, "upi": 0.0, "card": 0.0}

    for tenant_id in tenant_ids:
        async with _session(tenant_id) as session:
            data = await dashboard_repo_sql.charts_range(session, start, today, "UTC")
        for pt in data.get("series", {}).get("sales", []):
            agg_sales[pt["d"]] = agg_sales.get(pt["d"], 0.0) + pt["v"]
        for pt in data.get("series", {}).get("orders", []):
            agg_orders[pt["d"]] = agg_orders.get(pt["d"], 0) + pt["v"]
        for mode, amt in data.get("modes", {}).items():
            modes[mode] = modes.get(mode, 0.0) + amt

    dates = sorted(agg_sales.keys())
    sales_series = [{"d": d, "v": agg_sales.get(d, 0.0)} for d in dates]
    orders_series = [{"d": d, "v": agg_orders.get(d, 0)} for d in dates]
    avg_series = []
    for d in dates:
        s = agg_sales.get(d, 0.0)
        o = agg_orders.get(d, 0)
        avg_series.append({"d": d, "v": float(s / o) if o else 0.0})

    result = {
        "series": {
            "sales": sales_series,
            "orders": orders_series,
            "avg_ticket": avg_series,
        },
        "modes": modes,
    }
    await redis.set(cache_key, json.dumps(result), ex=300)
    return result


@router.get("/api/owner/{owner_id}/daybook.pdf")
@read_only
async def owner_daybook_pdf(owner_id: str, request: Request, date: str) -> Response:
    tenant_ids = _parse_scope(request)
    info = await _get_tenants_info(tenant_ids)
    day = datetime.strptime(date, "%Y-%m-%d").date()

    orders = 0
    subtotal = 0.0
    tax = 0.0
    tip = 0.0
    total = 0.0
    payments: dict[str, float] = {}
    outlet_totals: list[dict] = []

    for tenant_id in tenant_ids:
        tz = info.get(tenant_id, {}).get("tz", "UTC")
        name = info.get(tenant_id, {}).get("name", tenant_id)
        async with _session(tenant_id) as session:
            rows = await invoices_repo_sql.list_day(session, day, tz, tenant_id)
        orders += len(rows)
        subtotal_t = sum(r["subtotal"] for r in rows)
        tax_t = sum(r["tax"] for r in rows)
        tip_t = sum(r.get("tip", 0) for r in rows)
        total_t = sum(r["total"] for r in rows)
        subtotal += subtotal_t
        tax += tax_t
        tip += tip_t
        total += total_t
        for r in rows:
            for p in r["payments"]:
                payments[p["mode"]] = payments.get(p["mode"], 0.0) + p["amount"]
        outlet_totals.append({"name": name, "total": total_t})

    outlet_totals.sort(key=lambda x: x["total"], reverse=True)
    top_outlets = outlet_totals[:5]

    content, mimetype = render_template(
        "owner_daybook_a4.html",
        {
            "date": date,
            "orders": orders,
            "subtotal": subtotal,
            "tax": tax,
            "tip": tip,
            "total": total,
            "payments": payments,
            "top_outlets": top_outlets,
        },
    )
    response = Response(content=content, media_type=mimetype)
    ext = "pdf" if mimetype == "application/pdf" else "html"
    response.headers["Content-Disposition"] = f"attachment; filename=daybook.{ext}"
    return response
