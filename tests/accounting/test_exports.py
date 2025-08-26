from __future__ import annotations

import sys
import pathlib
import csv
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.db.tenant import get_engine
from api.app.models_tenant import Base, Category, MenuItem, OrderItem, Invoice
from api.app.routes_accounting_exports import router


async def _seed() -> None:
    tenant_id = "demo"
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        cat = Category(name="Food", sort=1)
        session.add(cat)
        await session.flush()
        item1 = MenuItem(
            category_id=cat.id,
            name="Item A",
            price=99,
            gst_rate=5,
            hsn_sac="1111",
        )
        item2 = MenuItem(
            category_id=cat.id,
            name="Item B",
            price=200,
            gst_rate=12,
            hsn_sac="2222",
        )
        session.add_all([item1, item2])
        await session.flush()
        oi1 = OrderItem(
            order_id=1,
            item_id=item1.id,
            name_snapshot=item1.name,
            price_snapshot=item1.price,
            qty=1,
            status="served",
        )
        oi2 = OrderItem(
            order_id=2,
            item_id=item2.id,
            name_snapshot=item2.name,
            price_snapshot=item2.price,
            qty=1,
            status="served",
        )
        session.add_all([oi1, oi2])
        await session.flush()
        inv1_total = Decimal("99.00") + Decimal("2.48") * 2
        inv2_total = Decimal("224.00")
        invoice1 = Invoice(
            order_group_id=1,
            number="INV1",
            bill_json={"inter_state": False},
            total=float(inv1_total),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        invoice2 = Invoice(
            order_group_id=2,
            number="INV2",
            bill_json={"inter_state": True},
            total=float(inv2_total),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        session.add_all([invoice1, invoice2])
        await session.commit()
    await engine.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_sales_register_exports(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    await _seed()

    app = FastAPI()
    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/accounting/sales_register.csv",
            params={"from": "2024-01-01", "to": "2024-01-01"},
        )
    lines = resp.text.splitlines()
    rows = list(csv.reader(lines))
    assert rows[0] == [
        "date",
        "invoice_no",
        "item",
        "hsn",
        "qty",
        "price",
        "taxable_value",
        "cgst",
        "sgst",
        "igst",
        "total",
    ]
    assert rows[1] == [
        "2024-01-01",
        "INV1",
        "Item A",
        "1111",
        "1",
        "99.00",
        "99.00",
        "2.48",
        "2.48",
        "0.00",
        "103.96",
    ]
    assert rows[2] == [
        "2024-01-01",
        "INV2",
        "Item B",
        "2222",
        "1",
        "200.00",
        "200.00",
        "0.00",
        "0.00",
        "24.00",
        "224.00",
    ]
    assert rows[3] == [
        "TOTAL",
        "",
        "",
        "",
        "",
        "",
        "299.00",
        "2.48",
        "2.48",
        "24.00",
        "327.96",
    ]


@pytest.mark.anyio
async def test_gst_summary_exports(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    await _seed()

    app = FastAPI()
    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/accounting/gst_summary.csv",
            params={"from": "2024-01-01", "to": "2024-01-01"},
        )
    rows = list(csv.reader(resp.text.splitlines()))
    assert rows[0] == ["hsn", "taxable_value", "cgst", "sgst", "igst", "total"]
    assert rows[1] == ["1111", "99.00", "2.48", "2.48", "0.00", "103.96"]
    assert rows[2] == ["2222", "200.00", "0.00", "0.00", "24.00", "224.00"]


@pytest.mark.anyio
async def test_gst_summary_composition(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    await _seed()

    app = FastAPI()
    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/accounting/gst_summary.csv",
            params={"from": "2024-01-01", "to": "2024-01-01", "composition": "true"},
        )
    rows = list(csv.reader(resp.text.splitlines()))
    assert rows[0] == ["hsn", "taxable_value", "cgst", "sgst", "igst", "total"]
    assert rows[1] == ["1111", "99.00", "0.00", "0.00", "0.00", "99.00"]
    assert rows[2] == ["2222", "200.00", "0.00", "0.00", "0.00", "200.00"]
