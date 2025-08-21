#!/usr/bin/env python3
"""Compute daily totals and enqueue a day-close notification.

The script calculates invoice totals for a given tenant and date using the
existing Z-report repository method and records an event in the ``sync_outbox``
table so that background workers can notify downstream systems.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import os
from typing import Dict

from api.app.db.tenant import get_tenant_session
from api.app.models_master import SyncOutbox
from api.app.repos_sqlalchemy import invoices_repo_sql


async def _compute_totals(session, day, tz: str) -> Dict:
    """Return aggregated totals for ``day`` in timezone ``tz``.

    This reuses the ``list_day`` helper from the invoices repository which is
    also used by the Z-report API endpoint.
    """

    rows = await invoices_repo_sql.list_day(session, day, tz)
    totals: Dict[str, float | Dict[str, float]] = {
        "subtotal": 0.0,
        "tax": 0.0,
        "total": 0.0,
        "payments": {},
    }
    for row in rows:
        totals["subtotal"] += row["subtotal"]
        totals["tax"] += row["tax"]
        totals["total"] += row["total"]
        for payment in row["payments"]:
            mode = payment["mode"]
            amt = payment["amount"]
            totals["payments"][mode] = totals["payments"].get(mode, 0.0) + amt
    return totals


async def main(tenant: str, date_str: str) -> None:
    """Compute totals for ``tenant`` on ``date_str`` and enqueue a notification."""

    day = datetime.strptime(date_str, "%Y-%m-%d").date()
    tz = os.getenv("DEFAULT_TZ", "UTC")
    async with get_tenant_session(tenant) as session:
        totals = await _compute_totals(session, day, tz)
        session.add(SyncOutbox(event_type="dayclose", payload=totals))
        await session.commit()
    print(totals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute day-close totals")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    asyncio.run(main(args.tenant, args.date))
