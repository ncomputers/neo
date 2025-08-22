#!/usr/bin/env python3
"""Purge expired PII and outbox entries for a tenant.

Environment variables:
- POSTGRES_MASTER_URL: SQLAlchemy URL for the master database.
- POSTGRES_TENANT_DSN_TEMPLATE: DSN template for tenant databases.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta

from pathlib import Path
import sys

from sqlalchemy import select, text

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.master import get_session as get_master_session  # type: ignore  # noqa: E402
from app.db.tenant import get_tenant_session  # type: ignore  # noqa: E402
from app.models_master import Tenant  # type: ignore  # noqa: E402


async def purge(tenant_name: str) -> None:
    async with get_master_session() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.name == tenant_name))
    if tenant is None:
        raise ValueError(f"Unknown tenant: {tenant_name}")

    tenant_id = str(tenant.id)
    now = datetime.utcnow()

    async with get_tenant_session(tenant_id) as t_session:
        if tenant.retention_days_customers:
            cutoff = now - timedelta(days=tenant.retention_days_customers)
            await t_session.execute(
                text("DELETE FROM customers WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
        if tenant.retention_days_outbox:
            cutoff = now - timedelta(days=tenant.retention_days_outbox)
            await t_session.execute(
                text(
                    "DELETE FROM notifications_outbox "
                    "WHERE status = 'delivered' AND created_at < :cutoff"
                ),
                {"cutoff": cutoff},
            )
        await t_session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge old tenant data")
    parser.add_argument("--tenant", required=True, help="Tenant name")
    args = parser.parse_args()
    asyncio.run(purge(args.tenant))


if __name__ == "__main__":
    main()

