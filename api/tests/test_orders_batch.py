"""Tests for batch order ingestion with idempotency."""

import os
import pathlib
import sys
import uuid

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import main as app_main  # noqa: E402
from api.app import routes_orders_batch  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.repos_sqlalchemy import orders_repo_sql  # noqa: E402


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


def test_batch_orders_idempotent_by_op_id(client):
    client, calls = client
    payload = {
        "orders": [
            {
                "op_id": str(uuid.uuid4()),
                "table_code": "T1",
                "items": [{"item_id": "1", "qty": 1}],
            }
            for _ in range(10)
        ]
    }

    resp1 = client.post("/api/outlet/demo/orders/batch", json=payload)
    assert resp1.status_code == 200
    assert calls["count"] == 10

    # Resubmit the same payload simulating a reconnect; op_ids should dedupe
    resp2 = client.post("/api/outlet/demo/orders/batch", json=payload)
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert calls["count"] == 10
