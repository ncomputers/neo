import io
import os
import pathlib
import sys
import zipfile
from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import models_tenant, routes_admin_export  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_session() -> AsyncSession:
    tenant_id = "demo"
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
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


app = FastAPI()
app.include_router(routes_admin_export.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.mark.anyio
async def test_admin_export_bundle(tenant_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield tenant_session

    monkeypatch.setattr(routes_admin_export, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/admin/export/data.zip",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "demo"},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    names = set(zipfile.ZipFile(io.BytesIO(resp.content)).namelist())
    expected = {"orders.csv", "order_items.csv", "items.csv", "customers.csv"}
    assert expected.issubset(names)
