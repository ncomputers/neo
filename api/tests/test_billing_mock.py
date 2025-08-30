import hashlib
import hmac
import json
import os
import sys
import types
from datetime import datetime, timedelta

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

# Stub optional dependencies not needed in tests
sys.modules.setdefault("opentelemetry", types.ModuleType("opentelemetry"))
sys.modules.setdefault("opentelemetry.trace", types.ModuleType("trace"))
sys.modules.setdefault("qrcode", types.ModuleType("qrcode"))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from api.app import billing  # noqa: E402
from api.app.billing import MockGateway  # noqa: E402
from api.app.main import TENANTS, app  # noqa: E402


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    TENANTS.clear()
    billing.SUBSCRIPTIONS.clear()
    billing.SUBSCRIPTION_EVENTS.clear()
    billing.INVOICES.clear()
    billing.PROCESSED_EVENTS.clear()


def _make_tenant(client):
    resp = client.post("/tenants", params={"name": "t1", "licensed_tables": 1})
    return resp.json()["data"]["tenant_id"]


def test_trial_expiry_and_renew(client):
    tenant_id = _make_tenant(client)
    headers = {"X-Tenant-ID": tenant_id}
    TENANTS[tenant_id]["subscription_expires_at"] = datetime.utcnow() - timedelta(
        days=5
    )
    resp = client.post("/orders", json={"tenant_id": tenant_id, "open_tables": 0})
    assert resp.status_code == 200  # within grace
    TENANTS[tenant_id]["subscription_expires_at"] = datetime.utcnow() - timedelta(
        days=8
    )
    resp = client.post("/orders", json={"tenant_id": tenant_id, "open_tables": 0})
    assert resp.status_code == 403
    resp = client.post(
        "/admin/billing/checkout", headers=headers, json={"plan_id": "starter"}
    )
    assert resp.status_code == 200
    resp = client.post("/orders", json={"tenant_id": tenant_id, "open_tables": 0})
    assert resp.status_code != 403


def test_webhook_signature_idempotency(client):
    payload = {"id": "evt1", "subscription_id": "s1", "type": "payment_succeeded"}
    body = json.dumps(payload).encode()
    sig = hmac.new(MockGateway.secret.encode(), body, hashlib.sha256).hexdigest()
    bad = hmac.new(b"bad", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/billing/webhook/mock", data=body, headers={"X-Mock-Signature": bad}
    )
    assert resp.status_code == 401
    resp = client.post(
        "/billing/webhook/mock", data=body, headers={"X-Mock-Signature": sig}
    )
    assert resp.status_code == 200
    assert len(billing.SUBSCRIPTION_EVENTS) == 1
    resp = client.post(
        "/billing/webhook/mock", data=body, headers={"X-Mock-Signature": sig}
    )
    assert resp.status_code == 200
    assert len(billing.SUBSCRIPTION_EVENTS) == 1
