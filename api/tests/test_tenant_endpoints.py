from __future__ import annotations

"""Smoke tests for tenant guest and KDS endpoints."""

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport

from api.app import main as app_main
from api.app.main import app
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from api.app import routes_guest_menu, routes_guest_order, routes_guest_bill, routes_kds
from api.app.repos_sqlalchemy import (
    orders_repo_sql,
    invoices_repo_sql,
    menu_repo_sql,
)
from contextlib import asynccontextmanager

# Use in-memory redis for rate limiting and other middleware
app.state.redis = fakeredis.aioredis.FakeRedis()


# Stub out DB-heavy repo functions
async def _fake_create_order(session, table_code, lines):
    return 1


async def _fake_generate_invoice(
    session, order_group_id, gst_mode, rounding, tenant_id
):
    return 1


async def _fake_get_tenant_session():
    class _DummySession:
        pass

    return _DummySession()


async def _fake_list_categories(self, session):
    return []


async def _fake_list_items(self, session, include_hidden=False):
    return [{"id": 1}]


@asynccontextmanager
async def _fake_kds_session(tenant_id: str):
    class _DummySession:
        pass

    yield _DummySession()


async def _fake_list_active(session):
    return []



@pytest.fixture(autouse=True)
def _override_deps():
    """Apply tenant overrides for guest routes."""

    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = (
        _fake_get_tenant_session
    )
    app.dependency_overrides[routes_guest_order.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_order.get_tenant_session] = (
        _fake_get_tenant_session
    )
    app.dependency_overrides[routes_guest_bill.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_bill.get_tenant_session] = (
        _fake_get_tenant_session
    )
    yield
    app.dependency_overrides.clear()



@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_tenant_guest_and_kds_flow(monkeypatch) -> None:
    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create_order)
    monkeypatch.setattr(invoices_repo_sql, "generate_invoice", _fake_generate_invoice)
    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "list_categories", _fake_list_categories
    )
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _fake_list_items)
    monkeypatch.setattr(routes_kds, "_session", _fake_kds_session)
    monkeypatch.setattr(orders_repo_sql, "list_active", _fake_list_active)
    """Ensure guest-facing menu, order, bill and KDS queue work."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Tenant-ID": "demo"}

        # fetch menu
        menu_resp = await client.get("/g/T-001/menu", headers=headers)
        assert menu_resp.status_code == 200
        menu_body = menu_resp.json()
        assert menu_body["ok"] is True
        assert isinstance(menu_body["data"]["items"], list)
        assert menu_body["data"]["items"]
        item_id = menu_body["data"]["items"][0]["id"]

        # place order
        order_resp = await client.post(
            "/g/T-001/order",
            headers=headers,
            json={"items": [{"item_id": str(item_id), "qty": 1}]},
        )
        assert order_resp.status_code == 200
        order_body = order_resp.json()
        assert order_body["ok"] is True
        order_id = order_body["data"]["order_id"]

        # generate bill
        bill_resp = await client.post(
            "/g/T-001/bill",
            headers=headers,
            json={"order_group_id": order_id},
        )
        assert bill_resp.status_code == 200
        assert bill_resp.json()["ok"] is True

        # kds queue should include active order(s)
        queue_resp = await client.get("/api/outlet/demo/kds/queue")
        assert queue_resp.status_code == 200
        queue_body = queue_resp.json()
        assert queue_body["ok"] is True
        assert isinstance(queue_body["data"], list)
