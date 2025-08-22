#!/usr/bin/env python3
"""Purge old tenant audit, notification and access log rows.

This helper removes historical data for a specific tenant. By default rows
older than 30 days are deleted from the following tables:

* ``audit_tenant`` – general audit trail of tenant actions.
* ``notifications_outbox`` – delivered notifications queued for outbound
  delivery.
* ``access_logs`` – request/usage logs recorded per tenant.

Only the most common columns are referenced so the script issues raw SQL
``DELETE`` statements instead of relying on ORM models. The goal is to keep
tenant databases lean while retaining recent activity for debugging or
reporting.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import text

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.tenant import get_tenant_session  # type: ignore  # noqa: E402


async def sweep(tenant: str, days: int = 30) -> None:
    """Delete rows older than ``days`` for ``tenant``.

    Parameters
    ----------
    tenant:
        Tenant identifier whose database should be cleaned.
    days:
        Retention window; rows older than this will be removed.
    """

    cutoff = datetime.utcnow() - timedelta(days=days)

    async with get_tenant_session(tenant) as session:
        await session.execute(
            text("DELETE FROM audit_tenant WHERE at < :cutoff"),
            {"cutoff": cutoff},
        )
        await session.execute(
            text(
                "DELETE FROM notifications_outbox "
                "WHERE status = 'delivered' AND delivered_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        await session.execute(
            text("DELETE FROM access_logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        await session.commit()


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Remove old tenant audit, outbox and access log data"
    )
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Retention window in days (default: 30)",
    )
    args = parser.parse_args()
    asyncio.run(sweep(args.tenant, args.days))


if __name__ == "__main__":
    _cli()

