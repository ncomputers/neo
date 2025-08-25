from __future__ import annotations

"""Owner cohort and retention analytics helpers."""

from datetime import date, timedelta
from typing import Dict, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.master import get_session as get_master_session
from ..db.tenant import get_tenant_session
from ..models_master import Tenant
from ..models_tenant import Order


async def _order_counts(session: AsyncSession) -> Dict[date, int]:
    """Return a mapping of order counts per day."""
    result = await session.execute(
        select(Order.placed_at).where(Order.placed_at.is_not(None))
    )
    counts: Dict[date, int] = {}
    for (placed_at,) in result.all():
        if placed_at is None:
            continue
        d = placed_at.date()
        counts[d] = counts.get(d, 0) + 1
    return counts


async def compute_owner_time_series(days: int = 30) -> dict:
    """Compute activation, retention and activity metrics over ``days``.

    The returned dictionary contains a ``series`` list with one entry per day
    starting from ``days`` ago up to today. Each entry exposes the following
    keys:

    ``activation_d0``
        Owners activated on the same day as creation.
    ``activation_d7``
        Owners activated within seven days of creation.
    ``activation_d30``
        Owners activated within thirty days of creation.
    ``retention_d7``
        Owners placing an order seven days after their first order.
    ``retention_d30``
        Owners placing an order thirty days after their first order.
    ``active_outlets``
        Count of outlets with orders on that day.
    ``avg_orders_per_outlet``
        Average orders per active outlet for the day.
    """

    today = date.today()
    start = today - timedelta(days=days - 1)
    activation_d0: Dict[date, int] = {}
    activation_d7: Dict[date, int] = {}
    activation_d30: Dict[date, int] = {}
    retention_d7: Dict[date, int] = {}
    retention_d30: Dict[date, int] = {}
    active_outlets: Dict[date, int] = {}
    orders_per_day: Dict[date, int] = {}

    try:
        async with get_master_session() as master_session:
            result = await master_session.execute(select(Tenant.id, Tenant.created_at))
            tenants: Iterable[tuple[str, date]] = [
                (str(tid), created_at.date()) for tid, created_at in result.all()
            ]
    except Exception:
        tenants = []

    for tenant_id, created_day in tenants:
        try:
            async with get_tenant_session(tenant_id) as t_session:
                counts = await _order_counts(t_session)
        except Exception:
            counts = {}
        if not counts:
            continue
        first_day = min(counts)
        diff = (first_day - created_day).days
        if diff == 0:
            activation_d0[created_day] = activation_d0.get(created_day, 0) + 1
        if diff <= 7:
            activation_d7[created_day] = activation_d7.get(created_day, 0) + 1
        if diff <= 30:
            activation_d30[created_day] = activation_d30.get(created_day, 0) + 1

        if first_day + timedelta(days=7) in counts:
            day = first_day + timedelta(days=7)
            retention_d7[day] = retention_d7.get(day, 0) + 1
        if first_day + timedelta(days=30) in counts:
            day = first_day + timedelta(days=30)
            retention_d30[day] = retention_d30.get(day, 0) + 1

        for day, count in counts.items():
            if day < start or day > today:
                continue
            active_outlets[day] = active_outlets.get(day, 0) + 1
            orders_per_day[day] = orders_per_day.get(day, 0) + count

    series = []
    for i in range(days):
        day = start + timedelta(days=i)
        active = active_outlets.get(day, 0)
        orders = orders_per_day.get(day, 0)
        avg = float(orders / active) if active else 0.0
        series.append(
            {
                "d": day.isoformat(),
                "activation_d0": activation_d0.get(day, 0),
                "activation_d7": activation_d7.get(day, 0),
                "activation_d30": activation_d30.get(day, 0),
                "retention_d7": retention_d7.get(day, 0),
                "retention_d30": retention_d30.get(day, 0),
                "active_outlets": active,
                "avg_orders_per_outlet": avg,
            }
        )
    return {"series": series}


__all__ = ["compute_owner_time_series"]
