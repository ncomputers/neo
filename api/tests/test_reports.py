from __future__ import annotations

import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import db as app_db
sys.modules.setdefault("db", app_db)

import csv
import io
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.app import routes_reports
from api.app.db.tenant import get_engine
from api.app import models_tenant
from api.app.models_tenant import Invoice, Payment

os.environ.setdefault("POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db")

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_session() -> AsyncSession:
    tenant_id = "test_" + uuid4().hex[:8]
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
app.include_router(routes_reports.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
async def seeded_session(tenant_session):
    invoice = Invoice(
        order_group_id=1,
        number="INV1",
        bill_json={"subtotal": 100.0, "tax_breakup": {5: 5.0}, "total": 105.0},
        total=105.0,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add(invoice)
    await tenant_session.flush()
    payment = Payment(
        invoice_id=invoice.id,
        mode="cash",
        amount=105.0,
        verified=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add(payment)
    await tenant_session.commit()
    return tenant_session


@pytest.mark.anyio
async def test_z_report_csv(seeded_session, monkeypatch):
    monkeypatch.setenv("DEFAULT_TZ", "UTC")

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_session

    monkeypatch.setattr(routes_reports, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/outlet/demo/reports/z?date=2024-01-01&format=csv")
        assert resp.status_code == 200
        rows = list(csv.reader(io.StringIO(resp.text)))
        assert rows[0] == ["invoice_no", "subtotal", "tax", "total", "payments", "settled"]
        assert rows[1] == ["INV1", "100.0", "5.0", "105.0", "cash:105.0", "True"]
