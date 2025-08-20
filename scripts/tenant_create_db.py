#!/usr/bin/env python3
"""Provision a tenant database or schema.

This is a lightweight CLI that ensures a tenant-specific database or schema
exists and runs migrations. The migrations hook is currently a stub.
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from db.tenant import build_dsn


async def ensure_database(engine, tenant_id: str) -> None:
    """Ensure the tenant database or schema exists.

    For now we simply attempt to create a schema matching the tenant ID. This
    will succeed if the database exists and the user has appropriate
    privileges. The logic can be extended later to create databases as needed.
    """

    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{tenant_id}"'))


async def run_tenant_migrations(engine) -> None:  # pragma: no cover - placeholder
    """Placeholder for running Alembic migrations."""
    # Implementation will be added in a future iteration.
    pass


async def main(tenant_id: str) -> None:
    dsn = build_dsn(tenant_id)
    engine = create_async_engine(dsn, isolation_level="AUTOCOMMIT")
    try:
        await ensure_database(engine, tenant_id)
        await run_tenant_migrations(engine)
    finally:
        await engine.dispose()
    print("READY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision a tenant database")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(main(args.tenant))
