#!/usr/bin/env python3
"""Send a daily KPI digest for a tenant.

Aggregates previous day's orders, sales, average ticket size,
 top selling items and payment split, and sends the digest
via configured providers. Supports ``console`` and ``whatsapp``
(stub) providers.

The script can be invoked directly or through the optional
API route ``POST /api/outlet/{tenant}/digest/run``.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, time, timedelta, timezone
import os
from typing import Iterable

from pathlib import Path
import sys

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.tenant import get_engine as get_tenant_engine  # type: ignore
from app.models_tenant import AuditTenant, Order, OrderItem, Invoice, Payment  # type: ignore
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zoneinfo import ZoneInfo
from api.app.routes_metrics import digest_sent_total  # type: ignore


class ConsoleProvider:
    """Provider that prints the digest to STDOUT."""

    @staticmethod
    def send(message: str) -> None:
        print(message)


class WhatsappProvider:
    """Stub provider for WhatsApp delivery."""

    @staticmethod
    def send(message: str) -> None:  # pragma: no cover - stub
        # In production this would send the message via WhatsApp.
        return None


PROVIDERS = {
    "console": ConsoleProvider(),
    "whatsapp": WhatsappProvider(),
}


async def build_digest_line(tenant: str, day: date) -> str:
    """Return a formatted digest line for ``tenant`` on ``day``."""
    tz = os.getenv("DEFAULT_TZ", "UTC")
    tzinfo = ZoneInfo(tz)
    start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
    end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

    engine = get_tenant_engine(tenant)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessionmaker() as session:
            orders = await _orders_count(session, start, end)
            sales = await _sales_total(session, start, end)
            avg_ticket = float(sales / orders) if orders else 0.0
            top_items = await _top_items(session, start, end)
            payments = await _payment_split(session, start, end)
            logins, cleaned = await _staff_activity(session, start, end)
    finally:
        await engine.dispose()

    top_str = ", ".join(f"{name}({qty})" for name, qty in top_items)
    pay_str = ", ".join(
        f"{mode}:{amount:.2f}" for mode, amount in sorted(payments.items())
    )
    return (
        f"{day.isoformat()} | orders={orders} | sales={sales:.2f} | "
        f"avg_ticket={avg_ticket:.2f} | top_items={top_str} | payments={pay_str} | "
        f"staff_logins={logins} | tables_cleaned={cleaned}"
    )


async def _orders_count(session: AsyncSession, start: datetime, end: datetime) -> int:
    result = await session.scalar(
        select(func.count()).select_from(Order).where(
            Order.placed_at >= start, Order.placed_at <= end
        )
    )
    return int(result or 0)


async def _sales_total(session: AsyncSession, start: datetime, end: datetime) -> float:
    result = await session.scalar(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.created_at >= start, Invoice.created_at <= end
        )
    )
    return float(result or 0)


async def _top_items(
    session: AsyncSession, start: datetime, end: datetime
) -> list[tuple[str, int]]:
    result = await session.execute(
        select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.placed_at >= start, Order.placed_at <= end)
        .group_by(OrderItem.name_snapshot)
        .order_by(desc("qty"))
        .limit(3)
    )
    return [(name, int(qty)) for name, qty in result.all()]


async def _payment_split(
    session: AsyncSession, start: datetime, end: datetime
) -> dict[str, float]:
    result = await session.execute(
        select(Payment.mode, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.created_at >= start, Payment.created_at <= end)
        .group_by(Payment.mode)
    )
    return {mode: float(amount or 0) for mode, amount in result.all()}


async def _staff_activity(
    session: AsyncSession, start: datetime, end: datetime
) -> tuple[int, int]:
    logins = await session.scalar(
        select(func.count()).where(
            AuditTenant.at >= start,
            AuditTenant.at <= end,
            AuditTenant.action == "login",
        )
    )
    cleaned = await session.scalar(
        select(func.count()).where(
            AuditTenant.at >= start,
            AuditTenant.at <= end,
            AuditTenant.action == "mark_table_ready",
        )
    )
    return int(logins or 0), int(cleaned or 0)


async def main(tenant: str, date_str: str | None = None, providers: Iterable[str] | None = None) -> str:
    """Compute digest for ``tenant``/``date`` and send via ``providers``.

    Returns the formatted digest line.
    """
    if date_str is None:
        tz = os.getenv("DEFAULT_TZ", "UTC")
        today = datetime.now(ZoneInfo(tz)).date()
        day = today - timedelta(days=1)
    else:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()

    line = await build_digest_line(tenant, day)

    for name in providers or ("console", "whatsapp"):
        provider = PROVIDERS.get(name)
        if provider:
            provider.send(line)
    digest_sent_total.inc()
    return line


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Send a daily KPI digest")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--date", help="Date in YYYY-MM-DD; defaults to yesterday")
    args = parser.parse_args()
    asyncio.run(main(args.tenant, args.date))


if __name__ == "__main__":
    _cli()
