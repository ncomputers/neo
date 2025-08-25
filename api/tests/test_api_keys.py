from __future__ import annotations

import os

import pytest
import pathlib
import sys

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import db as app_db
from api.app import models_tenant
from api.app.db.tenant import get_engine
from api.app.middlewares.api_key_auth import APIKeyAuthMiddleware
from api.app.routes_api_keys import router as api_keys_router

sys.modules.setdefault("db", app_db)

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
        else:  # pragma: no cover - non-sqlite cleanup
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
            await engine.dispose()


@pytest.fixture
async def client() -> AsyncClient:
    app = FastAPI()
    app.include_router(api_keys_router)

    @app.get("/api/outlet/{tenant_id}/reports/ping")
    async def ping(tenant_id: str):  # pragma: no cover - trivial
        return {"ok": True}

    app.add_middleware(APIKeyAuthMiddleware)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_api_key_crud_and_guard(
    client: AsyncClient, tenant_session: AsyncSession
):
    resp = await client.post("/api/outlet/demo/api-keys")
    assert resp.status_code == 200
    data = resp.json()["data"]
    key_id = data["id"]
    token = data["token"]

    resp = await client.get("/api/outlet/demo/api-keys")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1

    resp = await client.get("/api/outlet/demo/reports/ping")
    assert resp.status_code == 401

    resp = await client.get(
        "/api/outlet/demo/reports/ping", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200

    resp = await client.delete(f"/api/outlet/demo/api-keys/{key_id}")
    assert resp.status_code == 200

    resp = await client.get("/api/outlet/demo/api-keys")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
