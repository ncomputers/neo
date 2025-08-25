"""Tests for the owner daily export ZIP endpoint."""

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
from api.app import db as app_db  # noqa: E402

sys.modules.setdefault("db", app_db)  # noqa: E402
from api.app import models_tenant, routes_exports  # noqa: E402
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
app.include_router(routes_exports.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
async def seeded_session(tenant_session):
    inv1 = Invoice(
        order_group_id=1,
        number="INV1",
        bill_json={
            "number": "INV1",
            "items": [{"name": "Item1", "price": 50.0, "qty": 2}],
            "subtotal": 100.0,
            "tax_breakup": {5: 5.0},
            "total": 105.0,
        },
        tip=0,
        total=105.0,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    inv2 = Invoice(
        order_group_id=2,
        number="INV2",
        bill_json={
            "number": "INV2",
            "items": [{"name": "Item2", "price": 25.0, "qty": 2}],
            "subtotal": 50.0,
            "tax_breakup": {5: 2.5},
            "total": 52.5,
        },
        tip=0,
        total=52.5,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add_all([inv1, inv2])
    await tenant_session.flush()
    pay1 = Payment(
        invoice_id=inv1.id,
        mode="cash",
        amount=105.0,
        verified=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    pay2 = Payment(
        invoice_id=inv2.id,
        mode="upi",
        amount=52.5,
        verified=False,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add_all([pay1, pay2])
    await tenant_session.commit()
    return tenant_session


@pytest.mark.anyio
async def test_daily_export_zip(seeded_session, monkeypatch):
    monkeypatch.setenv("DEFAULT_TZ", "UTC")

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_session

    monkeypatch.setattr(routes_exports, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-01"
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert "invoices.csv" in names
        assert "payments.csv" in names
        assert "z-report.csv" in names
        inv_rows = list(
            csv.reader(io.TextIOWrapper(zf.open("invoices.csv"), encoding="utf-8"))
        )
        pay_rows = list(
            csv.reader(io.TextIOWrapper(zf.open("payments.csv"), encoding="utf-8"))
        )
        z_rows = list(
            csv.reader(io.TextIOWrapper(zf.open("z-report.csv"), encoding="utf-8"))
        )
        assert len(inv_rows) > 1
        assert len(pay_rows) > 1
        assert len(z_rows) > 1


@pytest.mark.anyio
async def test_range_too_large(seeded_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_session

    monkeypatch.setattr(routes_exports, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-03-01"
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "RANGE_TOO_LARGE"


@pytest.fixture
async def large_seeded_session(tenant_session):
    invoices = []
    payments = []
    for i in range(12000):
        inv = Invoice(
            order_group_id=i,
            number=f"INV{i}",
            bill_json={"subtotal": 0, "tax_breakup": {}, "total": 0},
            tip=0,
            total=0,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
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
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        )
    tenant_session.add_all(payments)
    await tenant_session.commit()
    return tenant_session


@pytest.mark.anyio
async def test_daily_export_cursor(large_seeded_session, monkeypatch):
    monkeypatch.setenv("DEFAULT_TZ", "UTC")

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield large_seeded_session

    monkeypatch.setattr(routes_exports, "_session", fake_session)
    monkeypatch.setattr(
        routes_exports,
        "render_invoice",
        lambda bill, size="80mm": (b"", "application/pdf"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        total = 0
        cursor = None
        for _ in range(3):
            url = (
                "/api/outlet/demo/exports/daily?"
                "start=2024-01-01&end=2024-01-01&limit=5000"
            )
            if cursor:
                url += f"&cursor={cursor}"
            resp = await client.get(url)
            assert resp.status_code == 200
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            inv_rows = list(
                csv.reader(
                    io.TextIOWrapper(zf.open("invoices.csv"), encoding="utf-8"),
                )
            )
            total += len(inv_rows) - 1
            cursor = resp.headers.get("x-cursor")
            if not cursor:
                break
        assert total == 12000
