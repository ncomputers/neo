import os
import sys
import types
from datetime import datetime, timedelta

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

# stub optional deps
sys.modules.setdefault("opentelemetry", types.ModuleType("opentelemetry"))
sys.modules.setdefault("opentelemetry.trace", types.ModuleType("trace"))
sys.modules.setdefault("qrcode", types.ModuleType("qrcode"))
sys.modules.setdefault("jwt", types.ModuleType("jwt"))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import api.app.main as app_main  # noqa: E402

TENANTS = app_main.TENANTS
app = app_main.app


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app_main.subscription_guard.ttl = 1
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    TENANTS.clear()


def _create_tenant(client) -> str:
    resp = client.post("/tenants", params={"name": "t1", "licensed_tables": 2})
    return resp.json()["data"]["tenant_id"]


def test_active_allows_orders(client):
    tid = _create_tenant(client)
    TENANTS[tid]["subscription_expires_at"] = datetime.utcnow() + timedelta(days=10)
    payload = {"tenant_id": tid, "open_tables": 0}
    headers = {"X-Tenant-ID": tid}
    resp = client.post("/orders", json=payload, headers=headers)
    assert resp.status_code == 200


def test_expired_blocks_orders(client):
    tid = _create_tenant(client)
    TENANTS[tid]["subscription_expires_at"] = datetime.utcnow() - timedelta(days=8)
    payload = {"tenant_id": tid, "open_tables": 0}
    headers = {"X-Tenant-ID": tid}
    resp = client.post("/orders", json=payload, headers=headers)
    assert resp.status_code == 402
    data = resp.json()
    assert data["error"]["message"]["code"] == "SUBSCRIPTION_EXPIRED"


def test_billing_route_bypass(client, monkeypatch):
    tid = _create_tenant(client)
    TENANTS[tid]["subscription_expires_at"] = datetime.utcnow() - timedelta(days=8)
    headers = {"X-Tenant-ID": tid}
    resp = client.get("/admin/billing/subscription", headers=headers)
    assert resp.status_code == 200


def test_cache_refresh_after_renewal(client):
    tid = _create_tenant(client)
    TENANTS[tid]["subscription_expires_at"] = datetime.utcnow() - timedelta(days=8)
    payload = {"tenant_id": tid, "open_tables": 0}
    headers = {"X-Tenant-ID": tid}
    resp = client.post("/orders", json=payload, headers=headers)
    assert resp.status_code == 402
    TENANTS[tid]["subscription_expires_at"] = datetime.utcnow() + timedelta(days=5)
    import time

    time.sleep(1.2)
    resp2 = client.post("/orders", json=payload, headers=headers)
    assert resp2.status_code == 200
