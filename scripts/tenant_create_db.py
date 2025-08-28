#!/usr/bin/env python3
"""Provision a tenant database or schema.

This is a lightweight CLI that ensures a tenant-specific database or schema
exists and runs migrations. The migrations hook is currently a stub.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure project root is on the import path so ``api.app`` resolves when
# invoked as ``python scripts/tenant_create_db.py`` with ``PYTHONPATH=api/app``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.app.db.tenant import build_dsn


async def ensure_schema(engine, tenant_id: str) -> None:
    """Ensure the tenant schema exists."""

    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{tenant_id}"'))


async def ensure_database_exists(dsn: str) -> None:
    """Create the tenant database if it is missing.

    The DSN is parsed to derive a server-level connection (``postgres``) that
    is used to issue ``CREATE DATABASE`` with ``AUTOCOMMIT``.
    """

    url = make_url(dsn)
    tenant_db = url.database
    admin_url = url.set(database="postgres")
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            res = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname=:name"),
                {"name": tenant_db},
            )
            if not res.scalar():
                await conn.execute(text(f'CREATE DATABASE "{tenant_db}"'))
    except Exception:
        await engine.dispose()
        admin_url = url.set(database="template1")
        engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        async with engine.begin() as conn:
            res = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname=:name"),
                {"name": tenant_db},
            )
            if not res.scalar():
                await conn.execute(text(f'CREATE DATABASE "{tenant_db}"'))
    finally:
        await engine.dispose()


async def run_tenant_migrations(engine) -> None:  # pragma: no cover - placeholder
    """Placeholder for running Alembic migrations."""
    # Implementation will be added in a future iteration.
    pass


async def main(tenant_id: str) -> None:
    dsn = build_dsn(tenant_id)
    await ensure_database_exists(dsn)
    engine = create_async_engine(dsn, isolation_level="AUTOCOMMIT")
    try:
        await ensure_schema(engine, tenant_id)
        await run_tenant_migrations(engine)
    finally:
        await engine.dispose()
    print("READY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision a tenant database")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(main(args.tenant))
