import pathlib
import sys
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

import fakeredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import models_tenant
from api.app.models_tenant import Invoice, Order, OrderItem, OrderStatus, Payment
from api.app import routes_owner_aggregate


async def _seed(amount: float, prep: int) -> tuple[AsyncSession, any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = Session()
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    item_name = "Burger" if amount == 100 else "Fries"
    for i in range(3):
        placed = base + timedelta(days=i)
        order = Order(
            table_id=1,
            status=OrderStatus.NEW,
            placed_at=placed,
            accepted_at=placed,
            ready_at=placed + timedelta(seconds=prep),
        )
        session.add(order)
        await session.flush()
        session.add(
            OrderItem(
                order_id=order.id,
                item_id=1,
                name_snapshot=item_name,
                qty=1,
                price_snapshot=amount - 5,
                status="served",
            )
        )
        bill = {"subtotal": amount - 5, "tax_breakup": {5: 5}, "total": amount}
        invoice = Invoice(
            order_group_id=order.id,
            number=f"INV{i}",
            bill_json=bill,
            gst_breakup=bill["tax_breakup"],
            total=amount,
            created_at=placed,
        )
        session.add(invoice)
        await session.flush()
        session.add(
            Payment(
                invoice_id=invoice.id,
                mode="cash",
                amount=amount,
                created_at=placed,
            )
        )
    await session.commit()
    return session, engine


@pytest.fixture
async def seeded_sessions():
    s1, e1 = await _seed(100, 600)
    s2, e2 = await _seed(200, 1200)
    yield {"t1": s1, "t2": s2}
    await s1.close()
    await s2.close()
    await e1.dispose()
    await e2.dispose()


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(routes_owner_aggregate.router)
    app.state.redis = fakeredis.aioredis.FakeRedis()
    return app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_summary_and_csv(app, seeded_sessions, monkeypatch):
    @asynccontextmanager
    async def fake_session(tid: str):
        yield seeded_sessions[tid]

    async def fake_info(ids):
        return {tid: {"tz": "UTC"} for tid in ids}

    monkeypatch.setattr(routes_owner_aggregate, "_session", fake_session)
    monkeypatch.setattr(routes_owner_aggregate, "_get_tenants_info", fake_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/analytics/outlets",
            params={"ids": "t1,t2", "from": "2024-01-01", "to": "2024-01-03"},
            headers={"x-tenant-ids": "t1,t2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["orders"] == 6
        assert data["sales"] == 900.0
        assert data["aov"] == 150.0
        assert data["median_prep"] == 900.0
        assert {"name": "Burger", "qty": 3} in data["top_items"]
        assert {"name": "Fries", "qty": 3} in data["top_items"]

        resp_csv = await client.get(
            "/api/analytics/outlets",
            params={
                "ids": "t1,t2",
                "from": "2024-01-01",
                "to": "2024-01-03",
                "format": "csv",
            },
            headers={"x-tenant-ids": "t1,t2"},
        )
        assert resp_csv.headers["content-type"].startswith("text/csv")
        body = resp_csv.text
        assert "t1,3,300.00,100.00,600.00" in body
        assert "t2,3,600.00,200.00,1200.00" in body


@pytest.mark.anyio
async def test_tenant_scope(app, seeded_sessions, monkeypatch):
    @asynccontextmanager
    async def fake_session(tid: str):
        yield seeded_sessions[tid]

    monkeypatch.setattr(routes_owner_aggregate, "_session", fake_session)

    async def fake_info(ids):
        return {tid: {"tz": "UTC"} for tid in ids}

    monkeypatch.setattr(routes_owner_aggregate, "_get_tenants_info", fake_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/analytics/outlets",
            params={"ids": "t1,t2", "from": "2024-01-01", "to": "2024-01-01"},
            headers={"x-tenant-ids": "t1"},
        )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_date_boundaries(app, seeded_sessions, monkeypatch):
    @asynccontextmanager
    async def fake_session(tid: str):
        yield seeded_sessions[tid]

    monkeypatch.setattr(routes_owner_aggregate, "_session", fake_session)

    async def fake_info(ids):
        return {tid: {"tz": "UTC"} for tid in ids}

    monkeypatch.setattr(routes_owner_aggregate, "_get_tenants_info", fake_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/analytics/outlets",
            params={"ids": "t1,t2", "from": "2024-01-02", "to": "2024-01-02"},
            headers={"x-tenant-ids": "t1,t2"},
        )
    data = resp.json()
    assert data["orders"] == 2
    assert data["sales"] == 300.0
    assert data["aov"] == 150.0
    assert data["median_prep"] == 900.0
