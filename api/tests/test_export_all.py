"""Tests for owner data portability export."""

from __future__ import annotations

import csv
import io
import os
import pathlib
import sys
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import models_tenant, routes_export_all  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402
from api.app.models_tenant import Invoice, Payment  # noqa: E402

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
app.include_router(routes_export_all.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.mark.anyio
async def test_export_all_bundle(tenant_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield tenant_session

    monkeypatch.setattr(routes_export_all, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "outlet_admin"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/export/all.zip",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = set(zf.namelist())
    expected = {
        "menu.csv",
        "items.csv",
        "orders.csv",
        "order_items.csv",
        "invoices.csv",
        "payments.csv",
        "customers.csv",
        "settings.json",
        "schema.json",
    }
    assert expected.issubset(names)


@pytest.fixture
async def large_seeded_session(tenant_session):
    invoices = []
    payments = []
    created = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(12000):
        inv = Invoice(
            order_group_id=i,
            number=f"INV{i}",
            bill_json={"subtotal": 0, "tax_breakup": {}, "total": 0},
            tip=0,
            total=0,
            created_at=created,
        )
        invoices.append(inv)
    tenant_session.add_all(invoices)
    await tenant_session.flush()
    for inv in invoices:
        payments.append(
            Payment(
                invoice_id=inv.id,
                mode="cash",
                amount=0,
                verified=True,
                created_at=created,
            )
        )
    tenant_session.add_all(payments)
    await tenant_session.commit()
    return tenant_session


@pytest.mark.anyio
async def test_export_all_streaming(large_seeded_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield large_seeded_session

    monkeypatch.setattr(routes_export_all, "_session", fake_session)
    monkeypatch.setattr(routes_export_all, "DEFAULT_LIMIT", 20000)

    token = create_access_token({"sub": "admin@example.com", "role": "outlet_admin"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET",
            "/api/outlet/demo/export/all.zip?limit=12000",
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            assert resp.status_code == 200
            chunks = [chunk async for chunk in resp.aiter_bytes()]
    data = b"".join(chunks)
    zf = zipfile.ZipFile(io.BytesIO(data))
    inv_rows = list(
        csv.reader(io.TextIOWrapper(zf.open("invoices.csv"), encoding="utf-8"))
    )
    assert len(inv_rows) - 1 == 12000
