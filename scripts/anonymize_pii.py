#!/usr/bin/env python3
"""Redact guest PII after N days.

This helper nulls out ``name``, ``phone`` and ``email`` columns in the
``customers`` and ``invoices`` tables for a specific tenant. Rows older than
the retention window are anonymized and a summary row is recorded in
``audit_tenant``.

Usage::

    python scripts/anonymize_pii.py --tenant TENANT_ID --days 30

Environment variables:

- ``POSTGRES_TENANT_DSN_TEMPLATE``: DSN template for tenant databases.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.tenant import get_tenant_session  # type: ignore  # noqa: E402
from app.models_tenant import AuditTenant  # type: ignore  # noqa: E402


async def anonymize(tenant: str, days: int = 30) -> None:
    """Anonymize guest PII for ``tenant``.

    Parameters
    ----------
    tenant:
        Tenant identifier whose database should be updated.
    days:
        Rows older than this many days will be anonymized.
    """

    cutoff = datetime.utcnow() - timedelta(days=days)

    async with get_tenant_session(tenant) as session:
        cust_res = await session.execute(
            text(
                "UPDATE customers SET name = NULL, phone = NULL, email = NULL "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        cust_count = cust_res.rowcount or 0

        inv_res = await session.execute(
            text(
                "UPDATE invoices SET name = NULL, phone = NULL, email = NULL "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        inv_count = inv_res.rowcount or 0

        session.add(
            AuditTenant(
                actor="system",
                action="anonymize_pii",
                meta={
                    "customers": cust_count,
                    "invoices": inv_count,
                    "cutoff": cutoff.isoformat(),
                },
            )
        )
        await session.commit()


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Redact guest PII after N days")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument(
        "--days", type=int, default=30, help="Retention window in days (default: 30)"
    )
    args = parser.parse_args()
    asyncio.run(anonymize(args.tenant, args.days))


if __name__ == "__main__":
    _cli()
