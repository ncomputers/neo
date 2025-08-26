from __future__ import annotations

import csv
import io
import os
import pathlib
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import db as app_db
from api.app import models_tenant, routes_accounting_exports

sys.modules.setdefault("db", app_db)
os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)
from api.app.db.tenant import get_engine
from api.app.models_tenant import (
    Category,
    Invoice,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_session() -> AsyncSession:
    engine = get_engine("demo")
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
            if db_path and db_path != ":memory":
                import os

                if os.path.exists(db_path):
                    os.remove(db_path)
        else:
            async with engine.begin() as conn:
                await conn.execute(text('DROP SCHEMA IF EXISTS "demo" CASCADE'))
            await engine.dispose()


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


@pytest.fixture
async def gst_seeded_session(tenant_session):
    cat = Category(name="Food", sort=1)
    tenant_session.add(cat)
    await tenant_session.flush()

    item1 = MenuItem(
        category_id=cat.id,
        name="Item1",
        price=100,
        gst_rate=5,
        hsn_sac="1001",
        is_veg=False,
    )
    item2 = MenuItem(
        category_id=cat.id,
        name="Item2",
        price=200,
        gst_rate=12,
        hsn_sac="2002",
        is_veg=False,
    )
    tenant_session.add_all([item1, item2])
    await tenant_session.flush()

    order = Order(table_id=1, status=OrderStatus.NEW)
    tenant_session.add(order)
    await tenant_session.flush()

    oi1 = OrderItem(
        order_id=order.id,
        item_id=item1.id,
        name_snapshot=item1.name,
        price_snapshot=item1.price,
        qty=2,
        status="served",
    )
    oi2 = OrderItem(
        order_id=order.id,
        item_id=item2.id,
        name_snapshot=item2.name,
        price_snapshot=item2.price,
        qty=1,
        status="served",
    )
    tenant_session.add_all([oi1, oi2])
    await tenant_session.flush()

    bill = {"subtotal": 400.0, "tax_breakup": {5: 10.0, 12: 24.0}, "total": 434.0}
    invoice = Invoice(
        order_group_id=order.id,
        number="INV1",
        bill_json=bill,
        gst_breakup=bill.get("tax_breakup"),
        total=bill["total"],
        created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
    )
    tenant_session.add(invoice)
    await tenant_session.commit()
    return tenant_session


@pytest.mark.anyio
async def test_sales_register_csv(seeded_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_session

    monkeypatch.setattr(routes_accounting_exports, "_session", fake_session)

    app = FastAPI()
    app.include_router(routes_accounting_exports.router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/accounting/sales_register.csv?from=2024-01-01&to=2024-01-01"
        )
        assert resp.status_code == 200
        rows = list(csv.reader(io.StringIO(resp.text)))
        assert rows[0] == ["date", "invoice_no", "subtotal", "tax", "total"]
        assert rows[1] == ["2024-01-01", "INV1", "100.0", "5.0", "105.0"]


@pytest.mark.anyio
async def test_gst_summary_csv(gst_seeded_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield gst_seeded_session

    monkeypatch.setattr(routes_accounting_exports, "_session", fake_session)

    app = FastAPI()
    app.include_router(routes_accounting_exports.router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/accounting/gst_summary.csv?from=2024-01-01&to=2024-01-31"
        )
        assert resp.status_code == 200
        rows = list(csv.reader(io.StringIO(resp.text)))
        assert rows[0] == [
            "gst_rate",
            "taxable_value",
            "cgst",
            "sgst",
            "igst",
            "total",
        ]
        assert rows[1] == ["5", "200.0", "5.0", "5.0", "0.0", "210.0"]
        assert rows[2] == ["12", "200.0", "12.0", "12.0", "0.0", "224.0"]
