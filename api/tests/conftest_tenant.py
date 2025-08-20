from __future__ import annotations

"""Test fixtures for tenant database setup."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tenant import get_engine
from scripts.tenant_create_db import run_tenant_migrations as _run_tenant_migrations


async def run_tenant_migrations(tenant_id: str) -> None:
    """Run migrations for a tenant using its identifier."""
    engine = get_engine(tenant_id)
    try:
        await _run_tenant_migrations(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def tenant_session() -> AsyncSession:
    """Provide an :class:`AsyncSession` bound to a temporary tenant database."""
    tenant_id = "test_" + uuid4().hex[:8]
    await run_tenant_migrations(tenant_id)

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with sessionmaker() as session:
            yield session
    finally:
        if engine.url.get_backend_name().startswith("sqlite"):
            await engine.dispose()
            db_path = engine.url.database
            if db_path and db_path != ":memory:" and os.path.exists(db_path):
                os.remove(db_path)
        else:
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
            await engine.dispose()
