#!/usr/bin/env python3
"""Utilities for managing table QR tokens.

This helper provides three subcommands:

* ``list_tables`` – list tables for a tenant.
* ``regen_qr`` – regenerate the QR token for a table.
* ``bulk_add_tables`` – create multiple tables with sequential codes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from sqlalchemy import select

from api.app.db.tenant import get_tenant_session
from api.app.models_tenant import Table


async def list_tables(tenant: str) -> list[dict[str, str]]:
    """Return a list of tables for ``tenant`` with their QR tokens."""

    async with get_tenant_session(tenant) as session:
        rows = await session.scalars(select(Table))
        tables = rows.all()
    return [
        {"id": str(t.id), "code": t.code or "", "qr_token": t.qr_token or ""}
        for t in tables
    ]


async def regen_qr(tenant: str, table_code: str) -> dict[str, str]:
    """Rotate the ``qr_token`` for ``table_code`` in ``tenant``."""

    async with get_tenant_session(tenant) as session:
        table = await session.scalar(select(Table).where(Table.code == table_code))
        if table is None:
            raise ValueError(f"Unknown table: {table_code}")
        old_token = table.qr_token
        table.qr_token = uuid.uuid4().hex
        await session.commit()
    return {
        "id": str(table.id),
        "code": table.code or "",
        "qr_token": table.qr_token or "",
        "old_token": old_token or "",
    }


async def bulk_add_tables(tenant: str, count: int) -> list[dict[str, str]]:
    """Insert ``count`` tables with sequential codes into ``tenant``."""

    async with get_tenant_session(tenant) as session:
        tables: list[Table] = []
        for i in range(1, count + 1):
            code = f"T-{i:03d}"
            table = Table(
                tenant_id=uuid.uuid4(),
                name=f"Table {i}",
                code=code,
                qr_token=uuid.uuid4().hex,
            )
            session.add(table)
            tables.append(table)
        await session.commit()
    return [
        {"id": str(t.id), "code": t.code or "", "qr_token": t.qr_token or ""}
        for t in tables
    ]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Tenant table QR utilities")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_list = subparsers.add_parser("list_tables", help="List tables for a tenant")
    p_list.add_argument("--tenant", required=True, help="Tenant identifier")

    p_regen = subparsers.add_parser("regen_qr", help="Regenerate QR token for a table")
    p_regen.add_argument("--tenant", required=True, help="Tenant identifier")
    p_regen.add_argument("--table", required=True, help="Table code")

    p_bulk = subparsers.add_parser(
        "bulk_add_tables", help="Add multiple tables with sequential codes"
    )
    p_bulk.add_argument("--tenant", required=True, help="Tenant identifier")
    p_bulk.add_argument(
        "--count", type=int, default=10, help="Number of tables to create"
    )

    args = parser.parse_args()

    if args.cmd == "list_tables":
        tables = await list_tables(args.tenant)
        print(json.dumps(tables))
    elif args.cmd == "regen_qr":
        info = await regen_qr(args.tenant, args.table)
        print(json.dumps(info))
    elif args.cmd == "bulk_add_tables":
        tables = await bulk_add_tables(args.tenant, args.count)
        print(json.dumps(tables))


if __name__ == "__main__":
    asyncio.run(main())
