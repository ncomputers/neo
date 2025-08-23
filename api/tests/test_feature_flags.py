"""Tests for hotel/counter feature flags middleware."""

from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.utils.responses import ok
from api.app.middlewares import feature_flags as ff_module


@app.get("/h/dummy")
async def _h_dummy():
    return ok({"mode": "hotel"})


@app.get("/c/dummy")
async def _c_dummy():
    return ok({"mode": "counter"})


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    return TestClient(app)


def test_features_disabled(client, monkeypatch):
    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    enable_hotel = False
                    enable_counter = False
                return _Tenant()
        yield _Session()

    monkeypatch.setattr(ff_module, "get_session", _session)

    headers = {"X-Tenant-ID": "demo", "Accept-Language": "hi"}
    resp = client.get("/h/dummy", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "FEATURE_OFF"
    assert body["error"]["message"] == "फ़ीचर बंद है"

    resp = client.get("/c/dummy", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "FEATURE_OFF"
    assert body["error"]["message"] == "फ़ीचर बंद है"


def test_features_enabled(client, monkeypatch):
    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    enable_hotel = True
                    enable_counter = True
                return _Tenant()
        yield _Session()

    monkeypatch.setattr(ff_module, "get_session", _session)

    headers = {"X-Tenant-ID": "demo"}
    resp = client.get("/h/dummy", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.get("/c/dummy", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
