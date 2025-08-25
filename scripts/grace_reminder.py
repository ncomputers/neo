#!/usr/bin/env python3
"""Send subscription expiry and grace period reminders.

Scans all active tenants in the master database and enqueues owner alerts when
subscriptions are due to expire in 7, 3 or 1 days, or while they remain within
their grace period. Notifications are routed via configured channels such as
email or WhatsApp.

Environment variables:
- POSTGRES_URL: SQLAlchemy URL for the master database.
- POSTGRES_TENANT_DSN_TEMPLATE: DSN template for tenant databases.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.models_master import Tenant  # type: ignore  # noqa: E402
from app.services import notifications  # type: ignore  # noqa: E402


async def run_once(engine) -> int:
    """Scan tenants and enqueue reminders.

    Returns the number of reminders queued.
    """

    now = datetime.utcnow()
    reminders = 0
    async with AsyncSession(engine) as session:
        rows = await session.execute(
            select(
                Tenant.name,
                Tenant.subscription_expires_at,
                Tenant.grace_period_days,
            ).where(Tenant.status == "active")
        )
        tenants = rows.all()

    for name, expires_at, grace in tenants:
        if expires_at is None:
            continue
        days = (expires_at.date() - now.date()).days
        if days in {7, 3, 1}:
            await notifications.enqueue(
                name,
                "billing.expiry.reminder",
                {"days": days},
            )
            reminders += 1
            continue
        if now > expires_at:
            grace_days = grace or 0
            grace_end = expires_at + timedelta(days=grace_days)
            if now <= grace_end:
                remaining = (grace_end.date() - now.date()).days
                await notifications.enqueue(
                    name,
                    "billing.grace",
                    {"remaining": remaining},
                )
                reminders += 1
    return reminders


async def run() -> int:
    """Entry point used by the systemd service."""

    master_url = os.environ["POSTGRES_URL"]
    engine = create_async_engine(master_url)
    try:
        return await run_once(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
