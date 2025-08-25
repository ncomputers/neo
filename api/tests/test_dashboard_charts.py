import asyncio
import time
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from api.app import models_tenant
from api.app.models_tenant import Order, Invoice, Payment, OrderStatus
from api.app import routes_dashboard_charts
from api.app.repos_sqlalchemy import dashboard_repo_sql

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def seeded_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        base = datetime(2024, 1, 1, 23, 0, tzinfo=timezone.utc)
        modes = ["cash", "upi", "card"]
        for i in range(10):
            placed = base + timedelta(days=i)
            order = Order(table_id=1, status=OrderStatus.NEW, placed_at=placed)
            session.add(order)
            await session.flush()
            invoice = Invoice(
                order_group_id=order.id,
                number=f"INV{i}",
                bill_json={"total": 10},
                total=10,
                created_at=placed,
            )
            session.add(invoice)
            await session.flush()
            payment = Payment(
                invoice_id=invoice.id,
                mode=modes[i % 3],
                amount=10,
                created_at=placed,
            )
            session.add(payment)
        await session.commit()
        yield session
    await engine.dispose()


app = FastAPI()
app.include_router(routes_dashboard_charts.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.mark.anyio
async def test_dashboard_charts_range(seeded_session, monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_session

    async def fake_tz(tenant_id: str) -> str:
        return "UTC"

    monkeypatch.setattr(routes_dashboard_charts, "_session", fake_session)
    monkeypatch.setattr(routes_dashboard_charts, "_get_timezone", fake_tz)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/outlet/demo/dashboard/charts?range=7")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["series"]["sales"]) == 7
    assert len(data["series"]["orders"]) == 7
    assert len(data["series"]["avg_ticket"]) == 7
    assert len(data["series"]["sales_ma7"]) == 7
    assert len(data["series"]["sales_ma30"]) == 7
    assert len(data["series"]["hourly_heatmap"]) == 24 * 7


@pytest.mark.anyio
async def test_dashboard_charts_cached(seeded_session, monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_session

    async def fake_tz(tenant_id: str) -> str:
        return "UTC"

    calls = 0
    original = dashboard_repo_sql.charts_range

    async def slow_charts(session, start, end, tz):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.1)
        return await original(session, start, end, tz)

    monkeypatch.setattr(routes_dashboard_charts, "_session", fake_session)
    monkeypatch.setattr(routes_dashboard_charts, "_get_timezone", fake_tz)
    monkeypatch.setattr(dashboard_repo_sql, "charts_range", slow_charts)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        t1 = time.perf_counter()
        await client.get("/api/outlet/demo/dashboard/charts?range=7")
        d1 = time.perf_counter() - t1
        t2 = time.perf_counter()
        await client.get("/api/outlet/demo/dashboard/charts?range=7")
        d2 = time.perf_counter() - t2
        await client.get("/api/outlet/demo/dashboard/charts?range=7&force=true")
    assert calls == 2
    assert d2 < d1


@pytest.mark.anyio
async def test_dashboard_charts_anomalies(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        base = datetime(2025, 8, 4, 23, 0, tzinfo=timezone.utc)
        for i in range(7):
            placed = base + timedelta(days=i)
            order = Order(table_id=1, status=OrderStatus.NEW, placed_at=placed)
            session.add(order)
            await session.flush()
            total = 100 if i == 6 else 10
            invoice = Invoice(
                order_group_id=order.id,
                number=f"INV{i}",
                bill_json={"total": total},
                total=total,
                created_at=placed,
            )
            session.add(invoice)
            await session.flush()
            payment = Payment(
                invoice_id=invoice.id,
                mode="cash",
                amount=total,
                created_at=placed,
            )
            session.add(payment)
        await session.commit()
        seeded = session

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded

    async def fake_tz(tenant_id: str) -> str:
        return "UTC"

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 8, 10, tzinfo=tz)

    monkeypatch.setattr(routes_dashboard_charts, "_session", fake_session)
    monkeypatch.setattr(routes_dashboard_charts, "_get_timezone", fake_tz)
    monkeypatch.setattr(routes_dashboard_charts, "datetime", FixedDatetime)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/outlet/demo/dashboard/charts?range=7&force=true")
    await engine.dispose()
    assert resp.status_code == 200
    data = resp.json()
    assert data["anomalies"] == ["2025-08-10"]
