import pathlib
import sys
from datetime import datetime, timezone

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from api.app import models_tenant
from api.app.models_tenant import Order, OrderItem, Invoice, OrderStatus, EMAStat
from api.app import routes_dashboard


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
        now = datetime.now(timezone.utc)
        order = Order(table_id=1, status=OrderStatus.NEW, placed_at=now)
        session.add(order)
        await session.flush()
        item = OrderItem(
            order_id=order.id,
            item_id=1,
            name_snapshot="Pizza",
            price_snapshot=10,
            qty=2,
            status="new",
        )
        session.add(item)
        invoice = Invoice(
            order_group_id=order.id,
            number="INV1",
            bill_json={"subtotal": 20, "tax_breakup": {}, "total": 20},
            total=20,
            created_at=now,
        )
        session.add(invoice)
        session.add(EMAStat(window_n=1, ema_seconds=30))
        await session.commit()
        yield session
    await engine.dispose()


app = FastAPI()
app.include_router(routes_dashboard.router)


@pytest.mark.anyio
async def test_dashboard_tiles(seeded_session, monkeypatch):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield seeded_session

    async def fake_tz(tenant_id: str) -> str:
        return "UTC"

    monkeypatch.setattr(routes_dashboard, "_session", fake_session)
    monkeypatch.setattr(routes_dashboard, "_get_timezone", fake_tz)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/outlet/demo/dashboard/tiles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["orders_today"] == 1
    assert data["sales_today"] == 20.0
    assert data["avg_eta_secs"] == 30.0
    assert data["top_items_today"] == [{"name": "Pizza", "qty": 2}]
