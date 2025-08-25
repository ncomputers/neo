"""Owner multi-outlet aggregate routes."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Iterable

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.master import get_read_session
from .db.tenant import get_engine
from .models_master import Tenant
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
    async with get_read_session() as session:
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


@router.get("/api/owner/{owner_id}/dashboard/charts")
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
