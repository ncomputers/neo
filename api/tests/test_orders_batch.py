"""Tests for batch order ingestion with idempotency."""

import sys
import pathlib
import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app
from api.app import main as app_main
from api.app import routes_orders_batch
from api.app.repos_sqlalchemy import orders_repo_sql


class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture
def client(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    original_guard = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(routes_orders_batch, "get_engine", lambda tid: engine)

    calls = {"count": 0}

    async def _fake_create(session, table_code, lines):
        calls["count"] += 1
        return calls["count"]

    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create)

    client = TestClient(app, raise_server_exceptions=False)
    yield client, calls

    app_main.subscription_guard = original_guard
    app.dependency_overrides.clear()


def test_batch_orders_idempotent(client):
    client, calls = client
    payload = {
        "orders": [
            {"table_code": "T1", "items": [{"item_id": "1", "qty": 1}]}
            for _ in range(10)
        ]
    }
    headers = {"Idempotency-Key": "abc"}

    resp1 = client.post("/api/outlet/demo/orders/batch", json=payload, headers=headers)
    assert resp1.status_code == 200
    assert calls["count"] == 10

    resp2 = client.post("/api/outlet/demo/orders/batch", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert calls["count"] == 10
