import builtins
import hashlib
import hmac
import os
import pathlib
import sys
import types
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
_webhooks_stub = types.ModuleType("routes_webhooks")
_webhooks_stub.router = None
sys.modules.setdefault("api.app.routes_webhooks", _webhooks_stub)
_menu_stub = types.ModuleType("menu")
_menu_stub.router = APIRouter()
_menu_stub.__path__ = []  # mark as package
sys.modules.setdefault("api.app.menu", _menu_stub)
_mod_stub = types.ModuleType("modifiers")
_mod_stub.apply_modifiers = lambda *args, **kwargs: None
sys.modules.setdefault("api.app.menu.modifiers", _mod_stub)
_diet_stub = types.ModuleType("dietary")
_diet_stub.filter_items = lambda *args, **kwargs: []
sys.modules.setdefault("api.app.menu.dietary", _diet_stub)
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
    tenant = types.SimpleNamespace(
        gateway_provider=provider or "none",
        gateway_sandbox=sandbox,
        subscription_expires_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, pk):
                return tenant

            async def commit(self):
                pass

        yield _Session()

    _session.tenant = tenant
    return _session


def test_start_disabled_env(client, monkeypatch):
    monkeypatch.delenv("ENABLE_GATEWAY", raising=False)
    monkeypatch.setattr(routes_checkout_gateway, "get_session", _master_session())
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    assert resp.status_code == 404


def test_start_disabled_tenant(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setattr(
        routes_checkout_gateway, "get_session", _master_session(provider=None)
    )
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    assert resp.status_code == 404


def test_start_success(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setattr(routes_checkout_gateway, "get_session", _master_session())
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pay_url"]


@pytest.mark.parametrize(
    "provider,secret_env",
    [("razorpay", "RAZORPAY_SECRET_TEST"), ("stripe", "STRIPE_SECRET_TEST")],
)
def test_webhook_signature_validation(provider, secret_env, client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setenv("GATEWAY_SANDBOX", "true")
    monkeypatch.setenv(secret_env, "secret")
    monkeypatch.setattr(
        routes_checkout_gateway, "get_session", _master_session(provider, True)
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
                return 1 if any(p.mode == "gateway_refund" for p in payments) else None

        return _Session()

    app.dependency_overrides[
        routes_checkout_gateway.get_tenant_session
    ] = _tenant_session

    amount = 10.0
    body = f"o1|1|{amount}|paid"
    sig = hmac.new(b"secret", body.encode(), hashlib.sha256).hexdigest()

    resp = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "order_id": "o1",
            "invoice_id": 1,
            "amount": 10,
            "status": "paid",
            "signature": sig,
        },
    )
    assert resp.status_code == 200
    assert payments and payments[0].invoice_id == 1

    resp_bad = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "order_id": "o1",
            "invoice_id": 1,
            "amount": 10,
            "status": "paid",
            "signature": "bad",
        },
    )
    assert resp_bad.status_code == 400


def test_refund_requires_idempotency_key(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setenv("GATEWAY_SANDBOX", "true")
    monkeypatch.setenv("RAZORPAY_SECRET_TEST", "secret")
    monkeypatch.setattr(
        routes_checkout_gateway, "get_session", _master_session("razorpay", True)
    )

    payments: list = []
    invoice = types.SimpleNamespace(settled=True, settled_at=None)

    async def _tenant_session(tenant: str):
        class _Session:
            async def get(self, model, pk):
                return invoice

            def add(self, obj):
                payments.append(obj)

            async def commit(self):
                pass

            async def scalar(self, stmt):
                return 1 if any(p.mode == "gateway_refund" for p in payments) else None

        return _Session()

    app.dependency_overrides[
        routes_checkout_gateway.get_tenant_session
    ] = _tenant_session

    order_id = "o1"
    sig_refund = hmac.new(
        b"secret", f"{order_id}|1|10.0|refund".encode(), hashlib.sha256
    ).hexdigest()

    resp = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "refund",
            "signature": sig_refund,
        },
    )
    assert resp.status_code == 400
    assert payments == []


def test_refund_duplicate_no_new_payment(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setenv("GATEWAY_SANDBOX", "true")
    monkeypatch.setenv("RAZORPAY_SECRET_TEST", "secret")
    monkeypatch.setattr(
        routes_checkout_gateway, "get_session", _master_session("razorpay", True)
    )

    payments: list = []
    invoice = types.SimpleNamespace(settled=True, settled_at=None)

    order_id = "o1"

    async def _tenant_session(tenant: str):
        class _Session:
            async def get(self, model, pk):
                return invoice

            def add(self, obj):
                payments.append(obj)

            async def commit(self):
                pass

            async def scalar(self, stmt):
                return 1 if payments else None

        return _Session()

    app.dependency_overrides[
        routes_checkout_gateway.get_tenant_session
    ] = _tenant_session

    sig_refund = hmac.new(
        b"secret", f"{order_id}|1|10.0|refund".encode(), hashlib.sha256
    ).hexdigest()

    resp1 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "refund",
            "signature": sig_refund,
        },
        headers={"Idempotency-Key": "key1"},
    )
    assert resp1.status_code == 200
    assert payments and payments[0].amount == -10

    resp2 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "refund",
            "signature": sig_refund,
        },
        headers={"Idempotency-Key": "key2"},
    )
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert len(payments) == 1


def test_e2e_start_webhook_flow(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setenv("GATEWAY_SANDBOX", "true")
    monkeypatch.setenv("RAZORPAY_SECRET_TEST", "secret")
    master_session = _master_session("razorpay", True)
    monkeypatch.setattr(routes_checkout_gateway, "get_session", master_session)

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
                return 1 if any(p.mode == "gateway_refund" for p in payments) else None

        return _Session()

    app.dependency_overrides[
        routes_checkout_gateway.get_tenant_session
    ] = _tenant_session

    # start checkout
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    order_id = resp.json()["data"]["order_id"]

    sig_paid = hmac.new(
        b"secret",
        f"{order_id}|1|10.0|paid".encode(),
        hashlib.sha256,
    ).hexdigest()

    # first webhook
    old_expiry = master_session.tenant.subscription_expires_at
    resp1 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
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
    assert master_session.tenant.subscription_expires_at > old_expiry

    # duplicate webhook should be idempotent
    resp2 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
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
    sig_refund = hmac.new(
        b"secret",
        f"{order_id}|1|10.0|refund".encode(),
        hashlib.sha256,
    ).hexdigest()
    refund_headers = {"Idempotency-Key": "key1"}
    resp3 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "refund",
            "signature": sig_refund,
        },
        headers=refund_headers,
    )
    assert resp3.status_code == 200
    assert not invoice.settled
    assert len(payments) == 2
    assert payments[1].amount == -10

    resp4 = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={
            "order_id": order_id,
            "invoice_id": 1,
            "amount": 10,
            "status": "refund",
            "signature": sig_refund,
        },
        headers=refund_headers,
    )
    assert resp4.status_code == 200
    assert resp4.json() == resp3.json()
    assert len(payments) == 2
