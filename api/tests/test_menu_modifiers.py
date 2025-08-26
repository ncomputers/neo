import asyncio
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from api.app.middlewares.security import SecurityMiddleware
from api.app.models_tenant import Base, Category, MenuItem, Counter, CounterOrderItem
from api.app import routes_guest_menu, routes_kot
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from fastapi import Depends
from api.app.repos_sqlalchemy import counter_orders_repo_sql

async def _setup_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        cat = Category(id=1, name="Snacks", sort=1)
        item = MenuItem(
            id=1,
            category_id=1,
            name="Tea",
            price=10,
            is_veg=False,
            modifiers=[{"id": 1, "name": "Sugar", "price": 2}, {"id": 2, "name": "Milk", "price": 3}],
            combos=[],
        )
        counter = Counter(id=1, code="C1", qr_token="ctr1")
        session.add_all([cat, item, counter])
        await session.commit()
        order_id = await counter_orders_repo_sql.create_order(
            session, "ctr1", [{"item_id": "1", "qty": 1, "mods": [1, 2]}]
        )
    return Session, order_id

Session, order_id = asyncio.run(_setup_db())

async def _session_dep(tenant_id: str = Depends(header_tenant_id)):
    async with Session() as session:
        yield session

def test_menu_modifiers_price_and_printable():
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.add_middleware(SecurityMiddleware)
    app.include_router(routes_guest_menu.router)
    app.include_router(routes_kot.router)
    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = _session_dep
    app.dependency_overrides[routes_kot.get_session_from_path] = _session_dep

    client = TestClient(app)
    resp = client.get("/g/T1/menu", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 200
    item = next(i for i in resp.json()["data"]["items"] if i["id"] == 1)
    assert len(item["modifiers"]) == 2

    async def _check_db():
        async with Session() as session:
            row = await session.scalar(
                select(CounterOrderItem).where(CounterOrderItem.order_id == order_id)
            )
            assert float(row.price_snapshot) == 15.0
            assert len(row.mods_snapshot) == 2
    asyncio.run(_check_db())

    resp2 = client.get(
        f"/api/outlet/demo/kot/{order_id}.pdf?size=80mm",
        headers={"X-Tenant-ID": "demo"},
    )
    assert resp2.status_code == 200
    text = resp2.text
    assert "Sugar" in text
    assert "Milk" in text
