import asyncio
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.app import routes_guest_menu
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from api.app.middlewares.security import SecurityMiddleware
from api.app.models_tenant import Base, Category, MenuItem


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
        cat = Category(id=1, name="Meals", sort=1)
        item1 = MenuItem(
            id=1,
            category_id=1,
            name="Veg Salad",
            price=10,
            is_veg=True,
            dietary=["vegan"],
            allergens=["nuts"],
        )
        item2 = MenuItem(
            id=2,
            category_id=1,
            name="Fruit Salad",
            price=12,
            is_veg=True,
            dietary=["vegan"],
            allergens=[],
        )
        item3 = MenuItem(
            id=3,
            category_id=1,
            name="Paneer Curry",
            price=15,
            is_veg=True,
            dietary=["vegetarian"],
            allergens=["dairy"],
        )
        session.add_all([cat, item1, item2, item3])
        await session.commit()
    return Session


Session = asyncio.run(_setup_db())


async def _session_dep(tenant_id: str = Depends(header_tenant_id)):
    async with Session() as session:
        yield session


def _client() -> TestClient:
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.add_middleware(SecurityMiddleware)
    app.include_router(routes_guest_menu.router)
    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = _session_dep
    return TestClient(app)


def test_filter_dietary_inclusion():
    client = _client()
    resp = client.get(
        "/g/T1/menu?filter=dietary:vegan", headers={"X-Tenant-ID": "demo"}
    )
    assert resp.status_code == 200
    names = {i["name"] for i in resp.json()["data"]["items"]}
    assert names == {"Veg Salad", "Fruit Salad"}


def test_filter_dietary_and_allergen_exclusion():
    client = _client()
    resp = client.get(
        "/g/T1/menu?filter=dietary:vegan,-allergen:nuts",
        headers={"X-Tenant-ID": "demo"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert [i["name"] for i in items] == ["Fruit Salad"]


def test_filter_multiple_inclusion():
    client = _client()
    resp = client.get(
        "/g/T1/menu?filter=dietary:vegan,allergen:nuts",
        headers={"X-Tenant-ID": "demo"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert [i["name"] for i in items] == ["Veg Salad"]
