from __future__ import annotations

"""Route for owner daybook PDF with HTML fallback."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, time
import os

from fastapi import APIRouter, Response, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zoneinfo import ZoneInfo

from .db.tenant import get_engine
from .models_tenant import OrderItem, Order
from .repos_sqlalchemy import invoices_repo_sql
from .pdf.render import render_template

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    """Yield an ``AsyncSession`` for the given tenant."""
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.get("/api/outlet/{tenant_id}/reports/daybook.pdf")
async def owner_daybook_pdf(tenant_id: str, date: str) -> Response:
    """Return a daily owner daybook in PDF or HTML format."""

    tz = os.getenv("DEFAULT_TZ", "UTC")
    day = datetime.strptime(date, "%Y-%m-%d").date()
    async with _session(tenant_id) as session:
        try:
            rows = await invoices_repo_sql.list_day(session, day, tz, tenant_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="forbidden") from None

        tzinfo = ZoneInfo(tz)
        start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
        end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)
        result = await session.execute(
            select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("qty"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.placed_at >= start, Order.placed_at <= end)
            .group_by(OrderItem.name_snapshot)
            .order_by(desc("qty"))
            .limit(5)
        )
        top_items = [{"name": name, "qty": int(qty)} for name, qty in result.all()]

    orders = len(rows)
    subtotal = sum(r["subtotal"] for r in rows)
    tax = sum(r["tax"] for r in rows)
    tip = sum(r.get("tip", 0) for r in rows)
    total = sum(r["total"] for r in rows)
    payments: dict[str, float] = {}
    for r in rows:
        for p in r["payments"]:
            payments[p["mode"]] = payments.get(p["mode"], 0) + p["amount"]

    content, mimetype = render_template(
        "daybook_a4.html",
        {
            "date": date,
            "orders": orders,
            "subtotal": subtotal,
            "tax": tax,
            "tip": tip,
            "total": total,
            "payments": payments,
            "top_items": top_items,
        },
    )
    response = Response(content=content, media_type=mimetype)
    ext = "pdf" if mimetype == "application/pdf" else "html"
    response.headers["Content-Disposition"] = f"attachment; filename=daybook.{ext}"
    return response
