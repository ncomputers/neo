#!/usr/bin/env python3
"""Send a daily owner digest for a tenant.

Summarises previous day's orders, average preparation time,
most popular items, complimentary counts, tip totals and the
number of webhook breaker opens. The digest is emitted via
providers – console, optional WhatsApp and optional email – if
their respective targets are configured in the environment.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from zoneinfo import ZoneInfo

from app.db.tenant import get_engine as get_tenant_engine  # type: ignore
from app.models_tenant import (  # type: ignore
    Invoice,
    Order,
    OrderItem,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import requests


class ConsoleProvider:
    """Provider that prints the digest to STDOUT."""

    @staticmethod
    def send(message: str) -> None:
        print(message)


class WhatsappProvider:
    """Stub provider for WhatsApp delivery.

    Requires ``OWNER_DIGEST_WA`` environment variable to be set
    with the destination identifier.
    """

    @staticmethod
    def send(message: str) -> None:  # pragma: no cover - stub
        target = os.getenv("OWNER_DIGEST_WA")
        if not target:
            return
        from api.app.providers import whatsapp_stub  # type: ignore

        whatsapp_stub.send("owner.digest", {"text": message}, target)


class EmailProvider:
    """Stub provider for email delivery.

    Requires ``OWNER_DIGEST_EMAIL`` environment variable to be
    set with the recipient address.
    """

    @staticmethod
    def send(message: str) -> None:  # pragma: no cover - stub
        target = os.getenv("OWNER_DIGEST_EMAIL")
        if not target:
            return
        from api.app.providers import email_stub  # type: ignore

        email_stub.send(
            "owner.digest", {"subject": "Owner Digest", "message": message}, target
        )


PROVIDERS = {
    "console": ConsoleProvider(),
    "whatsapp": WhatsappProvider(),
    "email": EmailProvider(),
}


async def build_digest_line(tenant: str, day: date) -> str:
    """Return a formatted digest line for ``tenant`` on ``day``."""
    tz = os.getenv("DEFAULT_TZ", "UTC")
    tzinfo = ZoneInfo(tz)
    start = datetime.combine(day, time.min, tzinfo).astimezone(timezone.utc)
    end = datetime.combine(day, time.max, tzinfo).astimezone(timezone.utc)

    engine = get_tenant_engine(tenant)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            orders = await _orders_count(session, start, end)
            avg_prep = await _avg_prep_minutes(session, start, end)
            top_items = await _top_items(session, start, end)
            comps = await _comps_count(session, start, end)
            tips = await _tips_total(session, start, end)
    finally:
        await engine.dispose()

    breaker = _breaker_opens()
    top_str = ", ".join(f"{name}({qty})" for name, qty in top_items)
    return (
        f"{day.isoformat()} | orders={orders} | avg_prep={avg_prep:.2f}m | "
        f"top_items={top_str} | comps={comps} | tips={tips:.2f} | "
        f"breaker_opens={breaker}"
    )


async def _orders_count(session: AsyncSession, start: datetime, end: datetime) -> int:
    result = await session.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.placed_at >= start, Order.placed_at <= end)
    )
    return int(result or 0)


async def _avg_prep_minutes(
    session: AsyncSession, start: datetime, end: datetime
) -> float:
    rows = await session.execute(
        select(Order.placed_at, Order.served_at).where(
            Order.served_at.is_not(None),
            Order.placed_at.is_not(None),
            Order.served_at >= start,
            Order.served_at <= end,
        )
    )
    durations = [
        (served - placed).total_seconds()
        for placed, served in rows.all()
        if placed and served
    ]
    return (sum(durations) / len(durations) / 60.0) if durations else 0.0


async def _top_items(
    session: AsyncSession, start: datetime, end: datetime
) -> list[tuple[str, int]]:
    result = await session.execute(
        select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.placed_at >= start, Order.placed_at <= end)
        .group_by(OrderItem.name_snapshot)
        .order_by(desc("qty"))
        .limit(5)
    )
    return [(name, int(qty)) for name, qty in result.all()]


async def _comps_count(session: AsyncSession, start: datetime, end: datetime) -> int:
    result = await session.scalar(
        select(func.count())
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.placed_at >= start,
            Order.placed_at <= end,
            OrderItem.price_snapshot == 0,
        )
    )
    return int(result or 0)


async def _tips_total(session: AsyncSession, start: datetime, end: datetime) -> float:
    result = await session.scalar(
        select(func.coalesce(func.sum(Invoice.tip), 0)).where(
            Invoice.created_at >= start, Invoice.created_at <= end
        )
    )
    return float(result or 0)


def _breaker_opens() -> int:
    url = os.getenv("METRICS_URL")
    if not url:
        base = os.getenv("PROXY_URL", "http://localhost:80").rstrip("/")
        url = f"{base}/metrics"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
    except Exception:
        return 0
    lines = resp.text.splitlines()
    return sum(
        1
        for line in lines
        if line.startswith("webhook_breaker_state") and line.strip().endswith(" 1")
    )


async def main(
    tenant: str,
    date_str: str | None = None,
    providers: Iterable[str] | None = None,
) -> str:
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

    for name in providers or ("console", "whatsapp", "email"):
        provider = PROVIDERS.get(name)
        if provider:
            provider.send(line)
    return line


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Send a daily owner digest")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--date", help="Date in YYYY-MM-DD; defaults to yesterday")
    args = parser.parse_args()
    asyncio.run(main(args.tenant, args.date))


if __name__ == "__main__":
    _cli()
