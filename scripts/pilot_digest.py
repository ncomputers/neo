#!/usr/bin/env python3
"""Send daily telemetry digest for pilot tenants."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure api package importable
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.tenant import get_tenant_engine  # type: ignore  # noqa: E402
from app.models_master import SyncOutbox  # type: ignore  # noqa: E402
from app.models_tenant import (  # type: ignore  # noqa: E402
    AuditTenant,
    NotificationDLQ,
    Order,
)
from app.providers import email_stub, slack_stub  # type: ignore  # noqa: E402

TZ_IST = ZoneInfo("Asia/Kolkata")


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min, TZ_IST).astimezone(timezone.utc)
    end = datetime.combine(d, time.max, TZ_IST).astimezone(timezone.utc)
    return start, end


async def _orders_count(session: AsyncSession, start: datetime, end: datetime) -> int:
    result = await session.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.placed_at >= start, Order.placed_at <= end)
    )
    return int(result or 0)


async def _failures_count(session: AsyncSession, start: datetime, end: datetime) -> int:
    result = await session.scalar(
        select(func.count())
        .select_from(NotificationDLQ)
        .where(
            NotificationDLQ.failed_at >= start,
            NotificationDLQ.failed_at <= end,
        )
    )
    return int(result or 0)


async def _sla_breaches(session: AsyncSession, start: datetime, end: datetime) -> int:
    result = await session.scalar(
        select(func.count())
        .select_from(AuditTenant)
        .where(
            AuditTenant.action == "kds_sla_breach",
            AuditTenant.at >= start,
            AuditTenant.at <= end,
        )
    )
    return int(result or 0)


async def _export_errors(start: datetime, end: datetime) -> int:
    master_url = os.environ.get("POSTGRES_URL")
    if not master_url:
        return 0
    engine = create_async_engine(master_url)
    try:
        async with AsyncSession(engine) as session:
            result = await session.scalar(
                select(func.count())
                .select_from(SyncOutbox)
                .where(
                    SyncOutbox.last_error.is_not(None),
                    SyncOutbox.created_at >= start,
                    SyncOutbox.created_at <= end,
                )
            )
    finally:
        await engine.dispose()
    return int(result or 0)


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


async def build_digest_line(
    tenant: str, day: date, start: datetime, end: datetime
) -> str:
    engine = get_tenant_engine(tenant)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            orders = await _orders_count(session, start, end)
            failures = await _failures_count(session, start, end)
            breaches = await _sla_breaches(session, start, end)
    finally:
        await engine.dispose()
    return f"{tenant}: orders={orders} failures={failures} sla_breaches={breaches}"


async def build_digest(tenants: Iterable[str], day: date) -> str:
    start, end = _day_bounds(day)
    lines = [f"Pilot digest {day.isoformat()}"]
    for tenant in tenants:
        lines.append(await build_digest_line(tenant, day, start, end))
    breakers = _breaker_opens()
    exports = await _export_errors(start, end)
    lines.append(f"breaker_opens={breakers} export_errors={exports}")
    message = "\n".join(lines)
    subject = f"Pilot digest {day.isoformat()}"
    email_target = os.getenv("PILOT_DIGEST_EMAIL")
    if email_target:
        email_stub.send(
            "pilot.digest", {"subject": subject, "message": message}, email_target
        )
    slack_target = os.getenv("PILOT_DIGEST_SLACK_CHANNEL")
    if slack_target:
        slack_stub.send("pilot.digest", {"text": message}, slack_target)
    return message


async def main(tenants: list[str], date_str: str | None = None) -> str:
    if date_str is None:
        today = datetime.now(TZ_IST).date()
        day = today - timedelta(days=1)
    else:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    return await build_digest(tenants, day)


def _parse_tenants(value: str | None) -> list[str]:
    if not value:
        return []
    return [t.strip() for t in value.split(",") if t.strip()]


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Send daily pilot telemetry digest")
    parser.add_argument("--tenants", help="Comma-separated pilot tenants")
    parser.add_argument("--date", help="Date in YYYY-MM-DD; defaults to yesterday")
    args = parser.parse_args()
    tenants = _parse_tenants(args.tenants) or _parse_tenants(os.getenv("PILOT_TENANTS"))
    if not tenants:
        raise SystemExit("no pilot tenants configured")
    asyncio.run(main(tenants, args.date))


if __name__ == "__main__":
    _cli()
