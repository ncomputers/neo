"""Tests for idempotency middleware on order routes."""

import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app
from api.app import routes_guest_order
from api.app.repos_sqlalchemy import orders_repo_sql
from api.app.deps.tenant import get_tenant_id as header_tenant_id


@pytest.fixture
def client(monkeypatch):
    """TestClient with stubbed tenant deps and FakeRedis."""

    app.state.redis = fakeredis.aioredis.FakeRedis()

    async def _fake_get_tenant_session():
        class _DummySession:
            pass
        return _DummySession()

    app.dependency_overrides[routes_guest_order.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_order.get_tenant_session] = (
        _fake_get_tenant_session
    )

    calls = {"n": 0}

    async def _fake_create_order(session, table_token, lines):
        calls["n"] += 1
        return 42

    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create_order)

    client = TestClient(app)
    yield client, calls
    app.dependency_overrides.clear()


def test_idempotent_guest_order(client):
    client, calls = client
    headers = {"X-Tenant-ID": "demo", "Idempotency-Key": "abc"}
    body = {"items": [{"item_id": "1", "qty": 1}]}

    first = client.post("/g/T-001/order", headers=headers, json=body)
    assert first.status_code == 200
    assert first.json()["data"]["order_id"] == 42
    assert calls["n"] == 1

    second = client.post("/g/T-001/order", headers=headers, json=body)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert calls["n"] == 1

    mismatch_body = {"items": [{"item_id": "1", "qty": 2}]}
    mismatch = client.post("/g/T-001/order", headers=headers, json=mismatch_body)
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMP_MISMATCH"
    assert calls["n"] == 1
