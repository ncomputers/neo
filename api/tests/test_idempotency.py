import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app
from api.app import main as app_main
from api.app import routes_guest_order
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from api.app.repos_sqlalchemy import orders_repo_sql


@pytest.fixture
def client(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    original_guard = app_main.subscription_guard

    async def _pass_through(request, call_next):
        return await call_next(request)

    app_main.subscription_guard = _pass_through

    async def _fake_get_tenant_session():
        class _DummySession:
            pass
        return _DummySession()

    app.dependency_overrides[routes_guest_order.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_order.get_tenant_session] = _fake_get_tenant_session

    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()
    app_main.subscription_guard = original_guard


def test_idempotent_order_returns_cached_response(client, monkeypatch):
    calls = 0

    async def _fake_create_order(session, table_token, lines):
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create_order)

    headers = {"X-Tenant-ID": "demo", "Idempotency-Key": "abc"}
    payload = {"items": [{"item_id": "1", "qty": 1}]}

    resp1 = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp1.status_code == 200

    resp2 = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert calls == 1
