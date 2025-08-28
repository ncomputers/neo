#!/usr/bin/env python3
"""Seed minimal menu data for a tenant.

This CLI inserts one category, two items and a single table with code
``"T-001"`` into the specified tenant database and prints the created
record identifiers as JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

# Ensure project root is on the import path so ``api.app`` resolves when
# invoked as ``python scripts/tenant_seed.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.app.db.tenant import get_tenant_session
from api.app.models_tenant import Category, MenuItem, Table


async def seed_minimal(session: AsyncSession) -> dict[str, int | str]:
    """Insert a minimal menu and table setup and return created IDs."""

    category = Category(name="Default", sort=1)
    session.add(category)
    await session.flush()

    veg_item = MenuItem(
        category_id=category.id, name="Veg Item", price=100, is_veg=True
    )
    non_veg_item = MenuItem(
        category_id=category.id, name="Non-Veg Item", price=150, is_veg=False
    )
    session.add_all([veg_item, non_veg_item])

    table = Table(tenant_id=uuid.uuid4(), name="Table 1", code="T-001")
    session.add(table)

    await session.commit()

    return {
        "category_id": category.id,
        "veg_item_id": veg_item.id,
        "non_veg_item_id": non_veg_item.id,
        "table_id": str(table.id),
    }


async def main(tenant_id: str) -> None:
    async with get_tenant_session(tenant_id) as session:
        ids = await seed_minimal(session)
    print(json.dumps(ids))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed minimal tenant data")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(main(args.tenant))
