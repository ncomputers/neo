#!/usr/bin/env python3
"""Create a demo takeaway counter for a tenant.

The script inserts a single counter with code ``TAKEAWAY`` and a unique QR
Token into the tenant's database. It prints the created record as JSON to make
it easy for developers to smoke test counter flows locally.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db.tenant import get_tenant_session
from api.app.models_tenant import Counter


async def seed_counter(session: AsyncSession) -> dict[str, int | str]:
    """Insert a takeaway counter and return its identifiers."""

    counter = Counter(code="TAKEAWAY", qr_token=uuid.uuid4().hex)
    session.add(counter)
    await session.flush()
    await session.commit()
    return {"id": counter.id, "code": counter.code, "qr_token": counter.qr_token}


async def main(tenant_id: str) -> None:
    async with get_tenant_session(tenant_id) as session:
        counter = await seed_counter(session)
    print(json.dumps({"counter": counter}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed a demo takeaway counter")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(main(args.tenant))
