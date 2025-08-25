#!/usr/bin/env python3
"""Scrub restored staging data of real PII.

This helper is intended to run on the staging environment after a
production restore. It replaces customer and invoice PII with obviously
fake placeholders, clears payment UTRs, rotates table, room, and counter
QR tokens, and marks all invoices as demo via a custom field.

Environment variables:
- ``POSTGRES_MASTER_URL``: SQLAlchemy URL for the master database.
- ``POSTGRES_TENANT_DSN_TEMPLATE``: DSN template for tenant databases.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select, text

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.db.master import (  # type: ignore  # noqa: E402
    get_session as get_master_session,
)
from app.db.tenant import get_tenant_session  # type: ignore  # noqa: E402
from app.models_master import Tenant  # type: ignore  # noqa: E402

FAKE_NAME = "Demo User"
FAKE_PHONE = "5550000000"
FAKE_EMAIL = "demo@example.com"


async def scrub_tenant(tenant_id: str) -> None:
    """Scrub PII for a single tenant database."""

    async with get_tenant_session(tenant_id) as session:
        # Replace customer and invoice PII with fakes
        await session.execute(
            text("UPDATE customers SET name = :name, phone = :phone, email = :email"),
            {"name": FAKE_NAME, "phone": FAKE_PHONE, "email": FAKE_EMAIL},
        )
        await session.execute(
            text(
                "UPDATE invoices "
                "SET name = :name, phone = :phone, email = :email, "
                "bill_json = jsonb_set("
                "bill_json::jsonb, '{custom_fields,demo}', 'true', true)"
            ),
            {"name": FAKE_NAME, "phone": FAKE_PHONE, "email": FAKE_EMAIL},
        )

        # Clear UTRs from payments
        await session.execute(text("UPDATE payments SET utr = NULL"))

        # Rotate QR tokens
        await session.execute(
            text("UPDATE counters SET qr_token = md5(random()::text || id::text)")
        )
        await session.execute(
            text("UPDATE tables SET qr_token = md5(random()::text || id::text)")
        )
        await session.execute(
            text("UPDATE rooms SET qr_token = md5(random()::text || id::text)")
        )

        await session.commit()


def _tenant_ids() -> list[str]:
    """Return all tenant identifiers from the master database."""

    async def _fetch() -> list[str]:
        async with get_master_session() as session:
            result = await session.execute(select(Tenant.id))
            return [str(row[0]) for row in result]

    return asyncio.get_event_loop().run_until_complete(_fetch())


async def scrub_all() -> None:
    """Scrub PII for all tenants."""

    for tenant_id in _tenant_ids():
        await scrub_tenant(tenant_id)


def main() -> None:
    asyncio.run(scrub_all())


if __name__ == "__main__":
    main()
