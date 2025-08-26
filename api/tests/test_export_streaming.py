"""Tests streaming of large daily exports."""

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


app = FastAPI()
app.include_router(routes_exports.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
async def large_seeded_session(tenant_session):
    """Seed the tenant DB with 12k invoices in batches."""
    created = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for batch in range(3):
        invoices = []
        payments = []
        base = batch * 1000
        for i in range(1000):
            inv = Invoice(
                order_group_id=base + i,
                number=f"INV{base + i}",
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
async def test_daily_export_streaming(large_seeded_session, monkeypatch):
    """Ensure streaming ZIP export handles 12k invoices without OOM."""
    monkeypatch.setenv("DEFAULT_TZ", "UTC")
    monkeypatch.setattr(routes_exports, "DEFAULT_LIMIT", 5000)
    monkeypatch.setattr(
        routes_exports, "render_invoice", lambda bill, size="80mm": (b"", "application/pdf")
    )

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield large_seeded_session

    monkeypatch.setattr(routes_exports, "_session", fake_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET",
            "/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-01&limit=3000",
        ) as resp:
            assert resp.status_code == 200
            chunks = [chunk async for chunk in resp.aiter_bytes()]
    data = b"".join(chunks)
    zf = zipfile.ZipFile(io.BytesIO(data))
    inv_rows = list(csv.reader(io.TextIOWrapper(zf.open("invoices.csv"), encoding="utf-8")))
    assert len(inv_rows) - 1 == 3000
