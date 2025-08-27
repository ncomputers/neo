"""Tests streaming CSV export progress, caps, and quotas."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import pathlib
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import db as app_db  # noqa: E402

sys.modules.setdefault("db", app_db)  # noqa: E402
from api.app import models_tenant, routes_exports  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402
from api.app.middlewares import licensing as lic_module  # noqa: E402
from api.app.models_tenant import Invoice  # noqa: E402

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)

app = FastAPI()
app.include_router(routes_exports.router)
app.add_middleware(lic_module.LicensingMiddleware)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_session() -> AsyncSession:
    tenant_id = "test_" + uuid4().hex[:8]
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
        else:  # pragma: no cover - postgres cleanup
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
            await engine.dispose()


@pytest.fixture
async def seeded_session_many(tenant_session):
    rows = [
        {
            "order_group_id": i,
            "number": f"INV{i}",
            "bill_json": {"subtotal": 0, "tax_breakup": {}, "total": 0},
            "tip": 0,
            "total": 0,
        }
        for i in range(11000)
    ]
    await tenant_session.execute(Invoice.__table__.insert(), rows)
    await tenant_session.commit()
    return tenant_session


@pytest.fixture
async def seeded_session_small(tenant_session):
    rows = [
        {
            "order_group_id": i,
            "number": f"INV{i}",
            "bill_json": {"subtotal": 0, "tax_breakup": {}, "total": 0},
            "tip": 0,
            "total": 0,
        }
        for i in range(10)
    ]
    await tenant_session.execute(Invoice.__table__.insert(), rows)
    await tenant_session.commit()
    return tenant_session


@pytest.mark.anyio
async def test_streaming_progress_over_10k(seeded_session_many, monkeypatch):
    """Ensure >10k export streams chunks and updates progress every 1000 rows."""

    orig_sleep = asyncio.sleep

    async def fast_sleep(_):
        await orig_sleep(0)

    monkeypatch.setattr(routes_exports.asyncio, "sleep", fast_sleep)

    class TrackingRedis(fakeredis.aioredis.FakeRedis):
        def __init__(self):
            super().__init__()
            self.progress: list[int] = []

        async def set(self, key, value, *args, **kwargs):  # type: ignore[override]
            if key == "export:bigjob:progress" and int(value):
                self.progress.append(int(value))
            return await super().set(key, value, *args, **kwargs)

    tracking = TrackingRedis()
    app.state.redis = tracking

    @asynccontextmanager
    async def fake_session(_tenant_id: str):
        yield seeded_session_many

    monkeypatch.setattr(routes_exports, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET", "/api/outlet/demo/exports/invoices.csv?limit=10500&job=bigjob"
        ) as resp:
            assert resp.status_code == 200
            assert (
                resp.headers.get("Transfer-Encoding") == "chunked"
                or resp.headers.get("Content-Length") is None
            )
            await resp.aread()
    assert tracking.progress == list(range(1000, 10001, 1000))


@pytest.mark.anyio
async def test_cap_hint_100k(seeded_session_many, monkeypatch):
    """Requesting >100k rows returns cap hint with HTTP 200."""

    app.state.redis = fakeredis.aioredis.FakeRedis()

    @asynccontextmanager
    async def fake_session(_tenant_id: str):
        yield seeded_session_many

    monkeypatch.setattr(routes_exports, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET", "/api/outlet/demo/exports/invoices.csv?limit=200000"
        ) as resp:
            assert resp.status_code == 200
            chunks = [chunk async for chunk in resp.aiter_bytes()]
    data = b"".join(chunks).decode().splitlines()
    assert data[-1].endswith("cap hit")


@pytest.mark.anyio
async def test_export_quota_respected(seeded_session_small, monkeypatch):
    """Daily export quota blocks subsequent requests."""

    app.state.redis = fakeredis.aioredis.FakeRedis()

    @asynccontextmanager
    async def fake_session(_tenant_id: str):
        yield seeded_session_small

    monkeypatch.setattr(routes_exports, "_session", fake_session)

    @asynccontextmanager
    async def _tenant_with_quota():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    id = tenant_id
                    plan = "pro"
                    status = "active"
                    grace_until = None
                    license_limits = {"max_daily_exports": 1}

                return _Tenant()

        yield _Session()

    monkeypatch.setattr(lic_module, "get_session", _tenant_with_quota)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Tenant-ID": "demo"}
        resp1 = await client.get(
            "/api/outlet/demo/exports/invoices.csv?limit=10", headers=headers
        )
        assert resp1.status_code == 200
        resp2 = await client.get(
            "/api/outlet/demo/exports/invoices.csv?limit=10", headers=headers
        )
        assert resp2.status_code == 403
        assert resp2.json()["error"]["code"] == "FEATURE_LIMIT"
