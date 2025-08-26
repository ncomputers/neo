import pathlib
import sys
import uuid

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))  # noqa: E402

import os  # noqa: E402

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.app import main as app_main  # noqa: E402
from api.app import routes_guest_order  # noqa: E402
from api.app.deps.tenant import get_tenant_id as header_tenant_id  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.repos_sqlalchemy import orders_repo_sql  # noqa: E402


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
    app.dependency_overrides[
        routes_guest_order.get_tenant_session
    ] = _fake_get_tenant_session

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

    headers = {"X-Tenant-ID": "demo", "Idempotency-Key": str(uuid.uuid4())}
    payload = {"items": [{"item_id": "1", "qty": 1}]}

    resp1 = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp1.status_code == 200

    resp2 = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert calls == 1


def test_rejects_invalid_idempotency_keys(client):
    headers = {"X-Tenant-ID": "demo", "Idempotency-Key": "bad-$$$"}
    payload = {"items": [{"item_id": "1", "qty": 1}]}
    resp = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_IDEMPOTENCY_KEY"


def test_rejects_long_idempotency_keys(client):
    headers = {"X-Tenant-ID": "demo", "Idempotency-Key": "a" * 129}
    payload = {"items": [{"item_id": "1", "qty": 1}]}
    resp = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_IDEMPOTENCY_KEY"


def test_creates_new_orders_without_key(client, monkeypatch):
    calls = 0

    async def _fake_create_order(session, table_token, lines):
        nonlocal calls
        calls += 1
        return calls

    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create_order)

    headers = {"X-Tenant-ID": "demo"}
    payload = {"items": [{"item_id": "1", "qty": 1}]}

    resp1 = client.post("/g/T-001/order", headers=headers, json=payload)
    resp2 = client.post("/g/T-001/order", headers=headers, json=payload)

    assert resp1.status_code == resp2.status_code == 200
    assert resp1.json() != resp2.json()
    assert calls == 2
