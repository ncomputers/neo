#!/usr/bin/env python3
"""Scan for KDS items breaching SLA and enqueue notifications.

Environment variables:
- POSTGRES_URL: SQLAlchemy URL for the master database.
- POSTGRES_TENANT_DSN_TEMPLATE: DSN template for tenant databases.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.tenant import get_tenant_session  # type: ignore  # noqa: E402
from app.models_master import Tenant  # type: ignore  # noqa: E402
from app.models_tenant import Order, OrderItem  # type: ignore  # noqa: E402
from app.services import notifications  # type: ignore  # noqa: E402


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def scan(tenant: str) -> int:
    """Scan ``tenant`` for items exceeding their SLA.

    Returns the number of breach notifications enqueued.
    """

    master_url = os.environ["POSTGRES_URL"]
    master_engine = create_async_engine(master_url)
    async with AsyncSession(master_engine) as msession:
        sla = (
            await msession.execute(
                select(Tenant.kds_sla_secs).where(Tenant.name == tenant)
            )
        ).scalar_one_or_none() or 900
    await master_engine.dispose()

    now = _now()
    breaches = 0
    delayed: list[tuple[int, int, float]] = []
    async with get_tenant_session(tenant) as session:
        result = await session.execute(
            select(OrderItem.id, Order.table_id)
                .join(Order, Order.id == OrderItem.order_id)
                .where(OrderItem.status == "in_progress")
        )
        for item_id, table_id in result.all():
            path = f"/api/outlet/{tenant}/kds/item/{item_id}/progress"
            last = await session.execute(
                text(
                    "SELECT max(at) FROM audit_tenant "
                    "WHERE action='progress_item' "
                    "AND json_extract(meta, '$.path') = :p"
                ),
                {"p": path},
            )
            last_at = last.scalar_one_or_none()
            if isinstance(last_at, str):
                last_at = datetime.fromisoformat(last_at)
            if last_at is None:
                continue
            if last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            delay = (now - last_at).total_seconds()
            if delay > sla:
                await notifications.enqueue(
                    tenant,
                    "kds.sla_breach",
                    {"order_item_id": item_id, "status": "in_progress"},
                )
                delayed.append((item_id, table_id, delay))
                breaches += 1
    if delayed:
        top_items = [
            i for i, _, _ in sorted(delayed, key=lambda x: x[2], reverse=True)[:3]
        ]
        table_counts = Counter(t for _, t, _ in delayed)
        top_tables = [t for t, _ in table_counts.most_common(3)]
        await notifications.enqueue(
            tenant,
            "kds.sla_breach.owner",
            {"items": top_items, "tables": top_tables},
        )
    return breaches


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Scan for KDS SLA breaches")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(scan(args.tenant))


if __name__ == "__main__":
    _cli()
