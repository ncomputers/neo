import asyncio
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.app.models_tenant import Base, Category, MenuItem
from api.app import routes_guest_menu
from api.app.deps.tenant import get_tenant_id as header_tenant_id


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
        items = [
            MenuItem(
                id=1,
                category_id=1,
                name="Tea",
                price=10,
                is_veg=True,
                dietary=["vegan"],
                allergens=[],
            ),
            MenuItem(
                id=2,
                category_id=1,
                name="Cake",
                price=20,
                is_veg=True,
                dietary=["vegetarian"],
                allergens=["nuts"],
            ),
            MenuItem(
                id=3,
                category_id=1,
                name="Salad",
                price=15,
                is_veg=True,
                dietary=["vegan"],
                allergens=["nuts"],
            ),
            MenuItem(
                id=4,
                category_id=1,
                name="Soup",
                price=12,
                is_veg=False,
                dietary=[],
                allergens=[],
            ),
        ]
        session.add(cat)
        session.add_all(items)
        await session.commit()
    return Session

Session = asyncio.run(_setup_db())


async def _session_dep(tenant_id: str = Depends(header_tenant_id)):
    async with Session() as session:
        yield session


def _make_app():
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.include_router(routes_guest_menu.router)
    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = _session_dep
    return app


def test_filters_intersect_and_negate():
    client = TestClient(_make_app())
    resp = client.get(
        "/g/T1/menu?filter=dietary:vegan,-allergen:nuts",
        headers={"X-Tenant-ID": "demo"},
    )
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["data"]["items"]]
    assert ids == [1]


def test_filter_excludes_allergen():
    client = TestClient(_make_app())
    resp = client.get(
        "/g/T1/menu?filter=-allergen:nuts",
        headers={"X-Tenant-ID": "demo"},
    )
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["data"]["items"]]
    assert 2 not in ids and 3 not in ids
    assert 1 in ids and 4 in ids
