import builtins
import hashlib
import hmac
import os
import pathlib
import sys
import types
from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

# ensure imports work
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
_webhooks_stub = types.ModuleType("routes_webhooks")
_webhooks_stub.router = None
sys.modules.setdefault("api.app.routes_webhooks", _webhooks_stub)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "https://example.com")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
builtins.webhook_tools_router = APIRouter()

from api.app import main as app_main  # noqa: E402
from api.app import routes_checkout_gateway  # noqa: E402
from api.app.main import app  # noqa: E402


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    original_guard = app_main.subscription_guard

    async def _pass(request, call_next):
        return await call_next(request)

    app_main.subscription_guard = _pass
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app_main.subscription_guard = original_guard
    app.dependency_overrides.clear()


def _master_session(provider: str | None = "razorpay", sandbox: bool = False):
    @asynccontextmanager
    async def _session():
        class _Tenant:
            gateway_provider = provider or "none"
            gateway_sandbox = sandbox

        class _Session:
            async def get(self, model, pk):
                return _Tenant()

        yield _Session()

    return _session


def test_sandbox_e2e(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setenv("GATEWAY_SANDBOX", "true")
    monkeypatch.setenv("RAZORPAY_SECRET_TEST", "secret")
    monkeypatch.setattr(
        routes_checkout_gateway, "get_session", _master_session("razorpay", True)
    )

    payments: list = []
    invoice = types.SimpleNamespace(settled=False, settled_at=None)

    async def _tenant_session(tenant: str):
        class _Session:
            async def get(self, model, pk):
                return invoice

            def add(self, obj):
                payments.append(obj)

            async def commit(self):
                pass

            async def scalar(self, stmt):
                event_id = stmt.whereclause.right.value
                return next((p for p in payments if p.utr == event_id), None)

        return _Session()

    app.dependency_overrides[
        routes_checkout_gateway.get_tenant_session
    ] = _tenant_session

    # start checkout
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    order_id = resp.json()["data"]["order_id"]

    # first webhook (paid)
    event_paid = "evt_1"
    sig_paid = hmac.new(
        b"secret", f"{order_id}|1|10.0|paid".encode(), hashlib.sha256
    ).hexdigest()
    resp1 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "event_id": event_paid,
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "paid",
            "signature": sig_paid,
        },
    )
    assert resp1.status_code == 200
    assert invoice.settled
    assert len(payments) == 1

    # duplicate webhook should be ignored
    resp2 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "event_id": event_paid,
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "paid",
            "signature": sig_paid,
        },
    )
    assert resp2.status_code == 200
    assert len(payments) == 1

    # refund webhook
    event_refund = "evt_2"
    sig_refund = hmac.new(
        b"secret", f"{order_id}|1|10.0|refund".encode(), hashlib.sha256
    ).hexdigest()
    resp3 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "event_id": event_refund,
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "refund",
            "signature": sig_refund,
        },
    )
    assert resp3.status_code == 200
    assert not invoice.settled
    assert len(payments) == 2
    assert payments[1].amount == -10
