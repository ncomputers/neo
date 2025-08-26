import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import db as app_db  # noqa: E402

sys.modules.setdefault("db", app_db)  # noqa: E402

from api.app import auth, models_tenant, routes_digest  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402
from api.app.models_tenant import (  # noqa: E402
    Category,
    Invoice,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
)

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
    db_path = engine.url.database
    if db_path and os.path.exists(db_path):
        os.remove(db_path)
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
            if db_path and db_path != ":memory:" and os.path.exists(db_path):
                os.remove(db_path)
        else:
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
            await engine.dispose()


@pytest.fixture
async def seeded_session(tenant_session):
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    cat = Category(name="Cat", sort=1)
    tenant_session.add(cat)
    await tenant_session.flush()
    menu_item = MenuItem(
        category_id=cat.id,
        name="Item",
        price=50,
        gst_rate=5,
        is_veg=False,
    )
    tenant_session.add(menu_item)
    await tenant_session.flush()
    order = Order(table_id=1, status=OrderStatus.NEW, placed_at=yesterday)
    tenant_session.add(order)
    await tenant_session.flush()
    item = OrderItem(
        order_id=order.id,
        item_id=menu_item.id,
        name_snapshot=menu_item.name,
        price_snapshot=menu_item.price,
        qty=1,
        status="served",
    )
    tenant_session.add(item)
    invoice = Invoice(
        order_group_id=order.id,
        number="INV1",
        bill_json={"subtotal": 50, "tax_breakup": {5: 2.5}, "total": 52.5},
        total=52.5,
        created_at=yesterday,
    )
    tenant_session.add(invoice)
    await tenant_session.flush()
    payment = Payment(
        invoice_id=invoice.id,
        mode="cash",
        amount=52.5,
        verified=True,
        created_at=yesterday,
    )
    tenant_session.add(payment)
    await tenant_session.commit()
    return tenant_session


app = FastAPI()
app.include_router(routes_digest.router)
app.state.redis = fakeredis.aioredis.FakeRedis()
app.dependency_overrides[auth.get_current_user] = lambda: auth.User(
    username="u", role="super_admin"
)


@pytest.mark.anyio
async def test_digest_route(seeded_session, monkeypatch):
    monkeypatch.setenv("DEFAULT_TZ", "UTC")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/outlet/demo/digest/run?date={yesterday}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] is True
    assert "console" in data["channels"]
    assert "email" in data["channels"]
