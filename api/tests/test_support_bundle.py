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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import text

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import db as app_db  # noqa: E402

sys.modules.setdefault("db", app_db)  # noqa: E402
from api.app import models_tenant, routes_support  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402
from api.app.models_tenant import AuditTenant  # noqa: E402

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)

app = FastAPI()
app.include_router(routes_support.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def audit_session() -> AsyncSession:
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


@pytest.fixture
async def seeded_audit_session(audit_session):
    audit_session.add_all(
        [AuditTenant(actor="u1", action="a1"), AuditTenant(actor="u2", action="a2")]
    )
    await audit_session.commit()
    return audit_session


@pytest.mark.anyio
async def test_support_bundle_zip(seeded_audit_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_audit_session

    monkeypatch.setattr(routes_support, "_tenant_session", fake_session)

    async def fake_config(tenant_id: str):
        return {"plan": "starter", "features": {}, "flags": {}}

    monkeypatch.setattr(routes_support, "_get_config", fake_config)

    app.dependency_overrides[routes_support.admin_required] = lambda: None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/outlet/demo/support/bundle.zip")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = set(zf.namelist())
        assert {
            "env.txt",
            "health.json",
            "ready.json",
            "version.json",
            "recent-logs.txt",
            "config.json",
        } <= names
