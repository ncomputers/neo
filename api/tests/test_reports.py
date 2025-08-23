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

from api.app import routes_reports, routes_gst_monthly, routes_daybook_pdf
from api.app.db.tenant import get_engine
from api.app import models_tenant
from api.app.models_tenant import (
    Invoice,
    Payment,
    Category,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
)
from api.app.services import billing_service

os.environ.setdefault("POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db")

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
app.include_router(routes_reports.router)
app.include_router(routes_gst_monthly.router)
app.include_router(routes_daybook_pdf.router)
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


@pytest.fixture
async def daybook_seeded_session(tenant_session):
    cat = Category(name="Food", sort=1)
    tenant_session.add(cat)
    await tenant_session.flush()

    pizza = MenuItem(
        category_id=cat.id,
        name="Pizza",
        price=100,
        gst_rate=5,
        is_veg=False,
    )
    pasta = MenuItem(
        category_id=cat.id,
        name="Pasta",
        price=50,
        gst_rate=5,
        is_veg=False,
    )
    tenant_session.add_all([pizza, pasta])
    await tenant_session.flush()

    order1 = Order(
        table_id=1,
        status=OrderStatus.NEW,
        placed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add(order1)
    await tenant_session.flush()

    oi1 = OrderItem(
        order_id=order1.id,
        item_id=pizza.id,
        name_snapshot=pizza.name,
        price_snapshot=pizza.price,
        qty=2,
        status="served",
    )
    oi2 = OrderItem(
        order_id=order1.id,
        item_id=pasta.id,
        name_snapshot=pasta.name,
        price_snapshot=pasta.price,
        qty=1,
        status="served",
    )
    tenant_session.add_all([oi1, oi2])
    await tenant_session.flush()

    bill1 = billing_service.compute_bill(
        [
            {"qty": 2, "price": 100, "gst": 5},
            {"qty": 1, "price": 50, "gst": 5},
        ],
        "reg",
        tip=10,
    )
    invoice1 = Invoice(
        order_group_id=order1.id,
        number="INV1",
        bill_json=bill1,
        gst_breakup=bill1.get("tax_breakup"),
        tip=bill1.get("tip", 0),
        total=bill1["total"],
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add(invoice1)
    await tenant_session.flush()

    payment1 = Payment(
        invoice_id=invoice1.id,
        mode="cash",
        amount=invoice1.total,
        verified=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    # Second order
    order2 = Order(
        table_id=2,
        status=OrderStatus.NEW,
        placed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add(order2)
    await tenant_session.flush()

    oi3 = OrderItem(
        order_id=order2.id,
        item_id=pizza.id,
        name_snapshot=pizza.name,
        price_snapshot=pizza.price,
        qty=1,
        status="served",
    )
    tenant_session.add(oi3)
    await tenant_session.flush()

    bill2 = billing_service.compute_bill(
        [
            {"qty": 1, "price": 100, "gst": 5},
        ],
        "reg",
    )
    invoice2 = Invoice(
        order_group_id=order2.id,
        number="INV2",
        bill_json=bill2,
        gst_breakup=bill2.get("tax_breakup"),
        tip=bill2.get("tip", 0),
        total=bill2["total"],
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    tenant_session.add(invoice2)
    await tenant_session.flush()

    payment2 = Payment(
        invoice_id=invoice2.id,
        mode="card",
        amount=invoice2.total,
        verified=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    tenant_session.add_all([payment1, payment2])
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

    bill = billing_service.compute_bill(
        [
            {"qty": 2, "price": 100, "gst": 5},
            {"qty": 1, "price": 200, "gst": 12},
        ],
        "reg",
    )
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


@pytest.mark.anyio
async def test_gst_monthly_report_csv(gst_seeded_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield gst_seeded_session

    monkeypatch.setattr(routes_gst_monthly, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/reports/gst/monthly?month=2024-01&gst_mode=reg"
        )
        assert resp.status_code == 200
        rows = list(csv.reader(io.StringIO(resp.text)))
        assert rows[0] == ["hsn", "taxable_value", "cgst", "sgst", "total"]
        assert rows[1] == ["1001", "200.0", "5.0", "5.0", "210.0"]
        assert rows[2] == ["2002", "200.0", "12.0", "12.0", "224.0"]
        assert rows[3] == ["TOTAL", "400.0", "17.0", "17.0", "434.0"]


@pytest.mark.anyio
async def test_daybook_pdf(daybook_seeded_session, monkeypatch):
    monkeypatch.setenv("DEFAULT_TZ", "UTC")

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield daybook_seeded_session

    monkeypatch.setattr(routes_daybook_pdf, "_session", fake_session)
    monkeypatch.setattr(routes_reports, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/reports/daybook.pdf?date=2024-01-01"
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html") or resp.headers[
            "content-type"
        ].startswith("application/pdf")
        body = resp.text
        resp_z = await client.get(
            "/api/outlet/demo/reports/z?date=2024-01-01&format=csv"
        )
        rows = list(csv.reader(io.StringIO(resp_z.text)))
        subtotal_z = sum(float(r[1]) for r in rows[1:])
        tax_z = sum(float(r[2]) for r in rows[1:])
        total_z = sum(float(r[3]) for r in rows[1:])
        assert "Orders: 2" in body
        assert f"Subtotal: {subtotal_z:.2f}" in body
        assert f"Tax: {tax_z:.2f}" in body
        assert "Tip: 10.00" in body
        assert f"Total: {total_z:.2f}" in body
        assert "cash" in body and "card" in body
        assert "Pizza" in body and "Pasta" in body


