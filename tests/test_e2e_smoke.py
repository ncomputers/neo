from __future__ import annotations

import pathlib
import sys

import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from api.app.main import app as fastapi_app
from api.app import main as app_main
from api.app import routes_guest_menu, routes_guest_order, routes_guest_bill, routes_kds
from api.app.repos_sqlalchemy import invoices_repo_sql, orders_repo_sql
from api.app.models_tenant import Base
import api.app.db as app_db
import api.app.middlewares.table_state_guard as table_state_guard
import api.app.middlewares.room_state_guard as room_state_guard
from tests._seed_tenant import seed_minimal_menu


class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture
async def app(tmp_path, monkeypatch):
    db_file = tmp_path / "tenant_demo.db"
    sync_engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=sync_engine)
    async_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Session = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

    monkeypatch.setattr(app_db, "engine", sync_engine)
    monkeypatch.setattr(app_db, "SessionLocal", SessionLocal)
    monkeypatch.setattr(app_main, "SessionLocal", SessionLocal)
    monkeypatch.setattr(table_state_guard, "SessionLocal", SessionLocal)
    monkeypatch.setattr(room_state_guard, "SessionLocal", SessionLocal)

    fastapi_app.state.redis = fakeredis.aioredis.FakeRedis()
    original_guard = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()
    fastapi_app.state.Session = Session
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()
    app_main.subscription_guard = original_guard
    await async_engine.dispose()
    sync_engine.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_e2e_smoke(app, monkeypatch):
    Session: async_sessionmaker[AsyncSession] = app.state.Session
    async with Session() as session:
        ids = await seed_minimal_menu(session)
    table_id = str(ids["table_id"])
    veg_item = str(ids["veg_item_id"])

    async def _session_dep():
        async with Session() as session:
            yield session

    async def _tenant_id() -> str:
        return "demo"

    app.dependency_overrides[routes_guest_menu.get_tenant_id] = _tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = _session_dep
    app.dependency_overrides[routes_guest_order.get_tenant_id] = _tenant_id
    app.dependency_overrides[routes_guest_order.get_tenant_session] = _session_dep
    app.dependency_overrides[routes_guest_bill.get_tenant_id] = _tenant_id
    app.dependency_overrides[routes_guest_bill.get_tenant_session] = _session_dep

    orders_state: dict[int, str] = {}

    async def _fake_create_order(session, table_code, lines):
        order_id = len(orders_state) + 1
        orders_state[order_id] = "placed"
        return order_id

    async def _fake_transition_order(tenant_id: str, order_id: int, dest):
        orders_state[order_id] = dest.value
        return routes_kds.ok({"status": dest.value})

    async def _fake_generate_invoice(*args, **kwargs):
        return 1

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create_order)
    monkeypatch.setattr(routes_kds, "_transition_order", _fake_transition_order)
    monkeypatch.setattr(routes_guest_order.event_bus, "publish", _noop)
    monkeypatch.setattr(app_main.event_bus, "publish", _noop)
    monkeypatch.setattr(invoices_repo_sql, "generate_invoice", _fake_generate_invoice)
    monkeypatch.setattr(routes_guest_bill.notifications, "enqueue", _noop)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        order_resp = await client.post(
            "/g/T-001/order", json={"items": [{"item_id": veg_item, "qty": 1}]}
        )
        assert order_resp.status_code == 200
        order_id = order_resp.json()["data"]["order_id"]

        resp = await client.post(f"/api/outlet/demo/kds/order/{order_id}/accept")
        assert resp.status_code == 200

        resp = await client.post(f"/api/outlet/demo/kds/order/{order_id}/ready")
        assert resp.status_code == 200

        resp = await client.post(f"/api/outlet/demo/kds/order/{order_id}/serve")
        assert resp.status_code == 200

        resp = await client.post("/g/T-001/bill")
        assert resp.status_code == 200

        resp = await client.post(f"/tables/{table_id}/pay")
        assert resp.status_code == 200

        resp = await client.post(f"/tables/{table_id}/lock")
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "LOCKED"

        resp = await client.post(f"/tables/{table_id}/mark-clean")
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "AVAILABLE"

        resp = await client.post(
            "/g/T-001/order", json={"items": [{"item_id": veg_item, "qty": 1}]}
        )
        assert resp.status_code == 200
