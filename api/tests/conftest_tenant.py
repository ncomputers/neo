# conftest_tenant.py
"""Tenant-scoped async session fixture for tests."""

from __future__ import annotations

import os
import pathlib
import sys
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.db.tenant import TEMPLATE_ENV, get_engine
from scripts.tenant_create_db import run_tenant_migrations as _run_tenant_migrations


async def run_tenant_migrations(tenant_id: str) -> None:
    """Run migrations for ``tenant_id`` using a temporary engine."""
    engine = get_engine(tenant_id)
    try:
        await _run_tenant_migrations(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def tenant_session():
    """Yield an ``AsyncSession`` bound to an isolated tenant database."""
    tenant_id = "test_" + uuid4().hex[:8]

    if not os.getenv(TEMPLATE_ENV):
        os.environ[TEMPLATE_ENV] = "sqlite+aiosqlite:///{tenant_id}.db"

    await run_tenant_migrations(tenant_id)

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        try:
            yield session
        finally:
            url = engine.url
            if url.get_backend_name() == "sqlite":
                await engine.dispose()
                db_path = url.database
                if db_path and db_path != ":memory:" and os.path.exists(db_path):
                    os.remove(db_path)
            else:
                async with engine.begin() as conn:
                    await conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
                await engine.dispose()
