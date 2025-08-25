from __future__ import annotations

import pathlib
import sys
from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import main as app_main  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.middlewares import licensing as lic_module  # noqa: E402
from api.app.utils.responses import ok  # noqa: E402


@app.get("/h/dummy")
async def _h_dummy():
    return ok({"mode": "hotel"})


@app.get("/c/dummy")
async def _c_dummy():
    return ok({"mode": "counter"})


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


def test_features_disabled(client, monkeypatch):
    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    plan = "starter"
                    status = "active"
                    grace_until = None

                return _Tenant()

        yield _Session()

    monkeypatch.setattr(lic_module, "get_session", _session)
    headers = {"X-Tenant-ID": "demo"}

    resp = client.get("/h/dummy", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FEATURE_NOT_IN_PLAN"

    resp = client.get("/c/dummy", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_features_enabled(client, monkeypatch):
    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    plan = "pro"
                    status = "active"
                    grace_until = None

                return _Tenant()

        yield _Session()

    monkeypatch.setattr(lic_module, "get_session", _session)
    headers = {"X-Tenant-ID": "demo"}

    resp = client.get("/h/dummy", headers=headers)
    assert resp.status_code == 200
    resp = client.get("/c/dummy", headers=headers)
    assert resp.status_code == 200
