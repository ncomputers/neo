"""Helpers for owner dashboard aggregates."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import List

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from ..models_tenant import Order, OrderItem, Invoice
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
