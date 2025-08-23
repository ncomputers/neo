from __future__ import annotations

from datetime import datetime, timezone
import sys
import pathlib

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from api.app.models_tenant import (
    Base,
    Category,
    MenuItem,
    OrderItem,
    Invoice,
)
from api.app.routes_gst_monthly import gst_monthly_report
from api.app.db.tenant import get_engine


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
            price=100,
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
            qty=2,
            status="served",
        )
        oi2 = OrderItem(
            order_id=1,
            item_id=item2.id,
            name_snapshot=item2.name,
            price_snapshot=item2.price,
            qty=1,
            status="served",
        )
        session.add_all([oi1, oi2])
        await session.flush()
        invoice = Invoice(
            order_group_id=1,
            number="INV1",
            bill_json={},
            total=0,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        session.add(invoice)
        await session.commit()
    await engine.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_gst_monthly_regular(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    await _seed()
    resp = await gst_monthly_report("demo", month="2024-01", gst_mode="reg")
    lines = resp.body.decode().splitlines()
    assert lines[0] == "hsn,taxable_value,cgst,sgst,total"
    assert lines[1] == "1111,200.0,5.0,5.0,210.0"
    assert lines[2] == "2222,200.0,12.0,12.0,224.0"
    assert lines[3] == "TOTAL,400.0,17.0,17.0,434.0"


@pytest.mark.anyio
async def test_gst_monthly_comp(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    await _seed()
    resp = await gst_monthly_report("demo", month="2024-01", gst_mode="comp")
    lines = resp.body.decode().splitlines()
    assert lines[0] == "description,taxable_value,total"
    assert lines[1] == "Total,400.0,400.0"


@pytest.mark.anyio
async def test_gst_monthly_unreg(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    await _seed()
    resp = await gst_monthly_report("demo", month="2024-01", gst_mode="unreg")
    lines = resp.body.decode().splitlines()
    assert lines[0] == "description,total"
    assert lines[1] == "Total,400.0"
