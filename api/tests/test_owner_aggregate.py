import pathlib
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import models_tenant
from api.app.models_tenant import Order, Invoice, Payment, OrderStatus
from api.app import routes_owner_aggregate


async def _seed(amount: float) -> tuple[AsyncSession, any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = Session()
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(7):
        placed = base + timedelta(days=i)
        order = Order(table_id=1, status=OrderStatus.NEW, placed_at=placed)
        session.add(order)
        await session.flush()
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
        payment = Payment(
            invoice_id=invoice.id,
            mode="cash",
            amount=amount,
            created_at=placed,
        )
        session.add(payment)
    await session.commit()
    return session, engine


@pytest.fixture
async def seeded_sessions():
    s1, e1 = await _seed(100)
    s2, e2 = await _seed(200)
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
async def test_owner_dashboard_charts(app, seeded_sessions, monkeypatch):
    @asynccontextmanager
    async def fake_session(tid: str):
        yield seeded_sessions[tid]

    async def fake_info(ids):
        return {tid: {"name": tid, "tz": "UTC"} for tid in ids}

    class FixedDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return datetime(2024, 1, 7)

    monkeypatch.setattr(routes_owner_aggregate, "_session", fake_session)
    monkeypatch.setattr(routes_owner_aggregate, "_get_tenants_info", fake_info)
    monkeypatch.setattr(routes_owner_aggregate, "datetime", FixedDatetime)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/owner/owner1/dashboard/charts?range=7",
            headers={"x-tenant-ids": "t1,t2"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["series"]["sales"]) == 7
    assert data["series"]["sales"][0]["v"] == 300.0
    assert data["series"]["orders"][0]["v"] == 2
    assert data["series"]["avg_ticket"][0]["v"] == 150.0
    assert data["modes"]["cash"] == 2100.0


@pytest.mark.anyio
async def test_owner_daybook_pdf(app, seeded_sessions, monkeypatch):
    @asynccontextmanager
    async def fake_session(tid: str):
        yield seeded_sessions[tid]

    async def fake_info(ids):
        return {
            "t1": {"name": "Outlet 1", "tz": "UTC"},
            "t2": {"name": "Outlet 2", "tz": "UTC"},
        }

    monkeypatch.setattr(routes_owner_aggregate, "_session", fake_session)
    monkeypatch.setattr(routes_owner_aggregate, "_get_tenants_info", fake_info)
    from api.app import repos_sqlalchemy

    monkeypatch.setattr(
        repos_sqlalchemy.TenantGuard, "assert_tenant", lambda *args, **kwargs: None
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/owner/owner1/daybook.pdf?date=2024-01-01",
            headers={"x-tenant-ids": "t1,t2"},
        )
    assert resp.status_code == 200
    body = resp.text
    assert "Orders: 2" in body
    assert "Subtotal: 290.00" in body
    assert "Tax: 10.00" in body
    assert "Total: 300.00" in body
    assert "Outlet 1" in body and "Outlet 2" in body
