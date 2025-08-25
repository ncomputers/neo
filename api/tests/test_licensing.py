"""Tests for licensing middleware enforcing plan gates and grace windows."""

from __future__ import annotations

import pathlib
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import main as app_main  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.middlewares import licensing as lic_module  # noqa: E402


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    original_guard = app_main.subscription_guard

    async def _pass(request, call_next):
        return await call_next(request)

    app_main.subscription_guard = _pass  # bypass old guard
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app_main.subscription_guard = original_guard


def test_grace_window(client, monkeypatch):
    @asynccontextmanager
    async def _grace_session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    plan = "starter"
                    status = "expired"
                    grace_until = datetime.utcnow() + timedelta(days=2)
                    features = {"exports": False}

                return _Tenant()

        yield _Session()

    monkeypatch.setattr(lic_module, "get_session", _grace_session)
    resp = client.get("/version", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 200
    assert resp.headers["X-Tenant-Plan"] == "starter"

    @asynccontextmanager
    async def _expired_session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    plan = "starter"
                    status = "expired"
                    grace_until = datetime.utcnow() - timedelta(seconds=1)
                    features = {"exports": False}

                return _Tenant()

        yield _Session()

    monkeypatch.setattr(lic_module, "get_session", _expired_session)
    resp = client.get("/version", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 402
    assert resp.json()["error"]["code"] == "LICENSE_EXPIRED"


def test_exports_feature_blocked(client, monkeypatch):
    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    plan = "starter"
                    status = "active"
                    grace_until = datetime.utcnow() + timedelta(days=2)
                    features = {"exports": False}

                return _Tenant()

        yield _Session()

    monkeypatch.setattr(lic_module, "get_session", _session)
    resp = client.get(
        "/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-01",
        headers={"X-Tenant-ID": "demo"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FEATURE_NOT_IN_PLAN"
