#!/usr/bin/env python3
"""Compute daily totals and enqueue a day-close notification.

This CLI aggregates invoice data for a given tenant and date using the
existing Z-report repository method and records a ``dayclose`` event in the
master database's sync outbox. The payload includes per-mode payment totals
and overall bill summaries.

"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.tenant import get_engine as get_tenant_engine  # type: ignore  # noqa: E402
from app.db.master import get_session as get_master_session  # type: ignore  # noqa: E402
from app.repos_sqlalchemy import invoices_repo_sql  # type: ignore  # noqa: E402
from app.models_master import SyncOutbox  # type: ignore  # noqa: E402


async def _compute_totals(tenant: str, date_str: str) -> dict:
    """Return aggregated invoice totals for ``tenant`` on ``date_str``."""
    tz = os.getenv("DEFAULT_TZ", "UTC")
    day = datetime.strptime(date_str, "%Y-%m-%d").date()

    engine = get_tenant_engine(tenant)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessionmaker() as session:
            rows = await invoices_repo_sql.list_day(session, day, tz, tenant)
    finally:
        await engine.dispose()

    totals = {"subtotal": 0.0, "tax": 0.0, "total": 0.0, "payments": {}}

    for row in rows:
        totals["subtotal"] += row["subtotal"]
        totals["tax"] += row["tax"]
        totals["total"] += row["total"]
        for p in row["payments"]:
            totals["payments"].setdefault(p["mode"], 0.0)
            totals["payments"][p["mode"]] += p["amount"]
    return totals


async def compute_and_enqueue(tenant: str, date_str: str) -> None:
    """Compute totals and enqueue a day-close notification in tenant DB."""
    totals = await _compute_totals(tenant, date_str)

    engine = get_tenant_engine(tenant)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        await session.run_sync(
            lambda s: SyncOutbox.__table__.create(bind=s.bind, checkfirst=True)
        )
        session.add(SyncOutbox(event_type="dayclose", payload=totals))
        await session.commit()
    await engine.dispose()


async def compute_and_enqueue_master(tenant: str, date_str: str) -> None:
    """Compute totals and enqueue a day-close notification in master DB."""
    totals = await _compute_totals(tenant, date_str)
    payload = {"tenant": tenant, "date": date_str, "totals": totals}

    async with get_master_session() as session:
        await session.run_sync(
            lambda s: SyncOutbox.__table__.create(bind=s.bind, checkfirst=True)
        )
        session.add(SyncOutbox(event_type="dayclose", payload=payload))
        await session.commit()


async def main(tenant: str, date: str) -> None:
    """Programmatic entrypoint used by tests."""

    await compute_and_enqueue(tenant, date)


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Compute daily totals and enqueue a day-close notification"
    )
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    asyncio.run(compute_and_enqueue_master(args.tenant, args.date))


if __name__ == "__main__":
    _cli()

