import pathlib
import sys
from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import main as app_main  # noqa: E402
from api.app import routes_checkout  # noqa: E402
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


def _master_session(enabled: bool):
    @asynccontextmanager
    async def _session():
        class _Tenant:
            enable_gateway = enabled

        class _Session:
            async def get(self, model, pk):
                return _Tenant()

        yield _Session()

    return _session


def test_start_disabled_env(client, monkeypatch):
    monkeypatch.delenv("ENABLE_GATEWAY", raising=False)
    monkeypatch.setattr(routes_checkout, "get_session", _master_session(True))
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    assert resp.status_code == 404


def test_start_disabled_tenant(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setattr(routes_checkout, "get_session", _master_session(False))
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    assert resp.status_code == 404


def test_start_success(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setattr(routes_checkout, "get_session", _master_session(True))
    resp = client.post(
        "/api/outlet/demo/checkout/start", json={"invoice_id": 1, "amount": 10}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pay_url"]


def test_webhook_attaches_payment(client, monkeypatch):
    monkeypatch.setenv("ENABLE_GATEWAY", "true")
    monkeypatch.setattr(routes_checkout, "get_session", _master_session(True))

    payments: list = []

    async def _tenant_session(tenant: str):
        class _Session:
            def add(self, obj):
                payments.append(obj)

            async def commit(self):
                pass

        return _Session()

    app.dependency_overrides[routes_checkout.get_tenant_session] = _tenant_session

    resp = client.post(
        "/api/outlet/demo/checkout/webhook",
        json={"order_id": "o1", "invoice_id": 1, "amount": 10, "signature": "s"},
    )
    assert resp.status_code == 200
    assert payments and payments[0].invoice_id == 1
