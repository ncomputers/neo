"""Helpers for owner dashboard aggregates."""
from __future__ import annotations

from datetime import date, datetime, time, timezone, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from ..models_tenant import Order, OrderItem, Invoice, Payment
from . import ema_repo_sql


async def tiles_today(session: AsyncSession, day: date, tz: str) -> dict:
    """Return dashboard tile metrics for ``day`` in ``tz`` timezone."""
    tzinfo = ZoneInfo(tz)
    start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
    end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

    orders_today = await session.scalar(
        select(func.count()).select_from(Order).where(
            Order.placed_at >= start, Order.placed_at <= end
        )
    )
    orders_today = int(orders_today or 0)

    sales_today = await session.scalar(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.created_at >= start, Invoice.created_at <= end
        )
    )
    sales_today = float(sales_today or 0)

    result = await session.execute(
        select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.placed_at >= start, Order.placed_at <= end)
        .group_by(OrderItem.name_snapshot)
        .order_by(desc("qty"))
        .limit(5)
    )
    top_items_today = [
        {"name": name, "qty": int(qty)} for name, qty in result.all()
    ]

    ema = await ema_repo_sql.load(session)
    avg_eta_secs = ema[1] if ema else 0.0

    return {
        "orders_today": orders_today,
        "sales_today": sales_today,
        "avg_eta_secs": avg_eta_secs,
        "top_items_today": top_items_today,
    }


async def charts_range(
    session: AsyncSession, start: date, end: date, tz: str
) -> dict:
    """Return time-series metrics and payment mix for ``start``–``end``.

    ``start`` and ``end`` are inclusive and interpreted in ``tz`` timezone.
    """

    tzinfo = ZoneInfo(tz)
    days = (end - start).days + 1

    sales_series = []
    orders_series = []
    avg_series = []
    # hourly heatmap accumulates sales per day/hour
    heatmap: dict[tuple[str, int], float] = {}
    for i in range(days):
        day = start + timedelta(days=i)
        s = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
        e = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

        orders = await session.scalar(
            select(func.count()).select_from(Order).where(
                Order.placed_at >= s, Order.placed_at <= e
            )
        )
        orders = int(orders or 0)

        sales = await session.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.created_at >= s, Invoice.created_at <= e
            )
        )
        sales = float(sales or 0)

        avg_ticket = float(sales / orders) if orders else 0.0
        ds = day.isoformat()
        sales_series.append({"d": ds, "v": sales})
        orders_series.append({"d": ds, "v": orders})
        avg_series.append({"d": ds, "v": avg_ticket})

    range_start = datetime.combine(start, time.min, tzinfo).astimezone(timezone.utc)
    range_end = datetime.combine(end, time.max, tzinfo).astimezone(timezone.utc)

    # gather invoice totals to build hourly heatmap
    result = await session.execute(
        select(Invoice.created_at, Invoice.total).where(
            Invoice.created_at >= range_start, Invoice.created_at <= range_end
        )
    )
    for created_at, total in result.all():
        local_dt = created_at.astimezone(tzinfo)
        key = (local_dt.date().isoformat(), local_dt.hour)
        heatmap[key] = heatmap.get(key, 0.0) + float(total or 0)

    heatmap_series = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        for h in range(24):
            v = heatmap.get((d, h), 0.0)
            heatmap_series.append({"d": d, "h": h, "v": v})

    result = await session.execute(
        select(Payment.mode, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.created_at >= range_start, Payment.created_at <= range_end)
        .group_by(Payment.mode)
    )
    modes = {"cash": 0.0, "upi": 0.0, "card": 0.0}
    for mode, amt in result.all():
        modes[mode] = float(amt or 0)

    return {
        "series": {
            "sales": sales_series,
            "orders": orders_series,
            "avg_ticket": avg_series,
            "hourly_heatmap": heatmap_series,
        },
        "modes": modes,
    }
