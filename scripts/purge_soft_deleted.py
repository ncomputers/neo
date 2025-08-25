#!/usr/bin/env python3
"""Hard delete soft-deleted tables and menu items.

Rows in ``tables`` and ``menu_items`` with a ``deleted_at`` timestamp older
than the specified retention window are permanently removed. A summary of the
operation is recorded in ``audit_tenant`` for each tenant. A dry-run mode is
available to log would-delete counts without modifying data.
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


async def purge(tenant: str, days: int = 90, dry_run: bool = False) -> None:
    """Hard delete long-soft-deleted rows for ``tenant``.

    Parameters
    ----------
    tenant:
        Tenant identifier whose database should be purged.
    days:
        Rows with ``deleted_at`` older than this many days will be removed.
    dry_run:
        If ``True``, only log counts of rows that would be deleted.
    """

    cutoff = datetime.utcnow() - timedelta(days=days)

    async with get_tenant_session(tenant) as session:
        if dry_run:
            tables_count = (
                await session.execute(
                    text("SELECT COUNT(*) FROM tables WHERE deleted_at < :cutoff"),
                    {"cutoff": cutoff},
                )
            ).scalar() or 0
            items_count = (
                await session.execute(
                    text("SELECT COUNT(*) FROM menu_items WHERE deleted_at < :cutoff"),
                    {"cutoff": cutoff},
                )
            ).scalar() or 0
            print(f"[dry-run] tables={tables_count} menu_items={items_count}")
            return

        tables_res = await session.execute(
            text("DELETE FROM tables WHERE deleted_at < :cutoff"),
            {"cutoff": cutoff},
        )
        items_res = await session.execute(
            text("DELETE FROM menu_items WHERE deleted_at < :cutoff"),
            {"cutoff": cutoff},
        )
        session.add(
            AuditTenant(
                actor="system",
                action="purge_soft_deleted",
                meta={
                    "tables": tables_res.rowcount or 0,
                    "menu_items": items_res.rowcount or 0,
                    "cutoff": cutoff.isoformat(),
                },
            )
        )
        await session.commit()
        print(
            "Deleted tables={} menu_items={}".format(
                tables_res.rowcount or 0, items_res.rowcount or 0
            )
        )


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Hard delete soft-deleted tables and menu items"
    )
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Retention window in days (default: 90)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only log counts without deleting",
    )
    args = parser.parse_args()
    asyncio.run(purge(args.tenant, args.days, args.dry_run))


if __name__ == "__main__":
    _cli()
