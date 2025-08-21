# test_guards_and_limits.py
"""Subscription guard and guest rate-limit tests."""

import pathlib
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest
import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import main as app_main
from api.app.main import app
from api.app import main as app_main
from api.app import routes_guest_menu, routes_guest_order
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from api.app.repos_sqlalchemy import menu_repo_sql, orders_repo_sql
from api.app.middlewares import subscription_guard as sg_module
from api.app.middlewares.subscription_guard import SubscriptionGuard
from api.app.security import ratelimit


@pytest.fixture
def client(monkeypatch):
    """Return TestClient with stubbed tenant dependencies and repos."""

    app.state.redis = fakeredis.aioredis.FakeRedis()
    original_guard = app_main.subscription_guard
    app_main.subscription_guard = SubscriptionGuard(app)
    async def _fake_get_tenant_session():
        class _DummySession:
            pass
        return _DummySession()

    # override tenant-aware dependencies
    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_order.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = (
        _fake_get_tenant_session
    )
    app.dependency_overrides[routes_guest_order.get_tenant_session] = (
        _fake_get_tenant_session
    )

    # stub out db-heavy repo calls
    async def _fake_list_categories(self, session):
        return []

    async def _fake_list_items(self, session, include_hidden=False):
        return [{"id": 1}]

    async def _fake_create_order(session, table_token, lines):
        return 1

    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_categories", _fake_list_categories)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _fake_list_items)
    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create_order)

    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()

    app_main.subscription_guard = original_guard


def test_subscription_expiry_blocks_order_but_allows_menu(client, monkeypatch):
    """Expired subscriptions block ordering but permit menu access."""

    @asynccontextmanager
    async def _expired_session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    subscription_expires_at = datetime.utcnow() - timedelta(days=30)
                    grace_period_days = 7
                return _Tenant()
        yield _Session()

    monkeypatch.setattr(sg_module, "get_session", _expired_session)

    headers = {"X-Tenant-ID": "demo"}

    # menu GET still allowed
    menu_resp = client.get("/g/T-001/menu", headers=headers)
    assert menu_resp.status_code == 200

    # ordering blocked with SUB_403 envelope
    order_headers = {**headers, "Idempotency-Key": "test"}
    order_resp = client.post(
        "/g/T-001/order", headers=order_headers, json={"items": [{"item_id": "1", "qty": 1}]}
    )
    assert order_resp.status_code == 403
    assert order_resp.json()["error"]["code"] == "SUB_403"


def test_guest_post_rate_limit(client, monkeypatch):
    """Guest POSTs are throttled when rate limit exceeded."""

    @asynccontextmanager
    async def _valid_session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    subscription_expires_at = datetime.utcnow() + timedelta(days=1)
                    grace_period_days = 7
                return _Tenant()
        yield _Session()

    monkeypatch.setattr(sg_module, "get_session", _valid_session)

    calls = {"n": 0}

    async def _allow(redis, ip, key, rate_per_min=60, burst=100):
        calls["n"] += 1
        return calls["n"] < 3

    monkeypatch.setattr(ratelimit, "allow", _allow)

    headers = {"X-Tenant-ID": "demo"}

    for i in range(2):
        resp = client.post(
            "/g/T-001/order",
            headers={**headers, "Idempotency-Key": f"k{i}"},
            json={"items": [{"item_id": "1", "qty": 1}]},
        )
        assert resp.status_code == 200

    # third request exceeds patched limit
    resp = client.post(
        "/g/T-001/order",
        headers={**headers, "Idempotency-Key": "k-final"},
        json={"items": [{"item_id": "1", "qty": 1}]},
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "RATELIMIT_429"
