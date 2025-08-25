"""Tests for per-tenant licensing quotas and usage endpoint."""

from __future__ import annotations

import os
import pathlib
import sys
from contextlib import asynccontextmanager
from io import BytesIO

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://user@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from api.app.main import app  # noqa: E402
from api.app.middlewares import licensing as lic_module  # noqa: E402

buf = BytesIO()
Image.new("RGB", (1, 1)).save(buf, format="PNG")
PNG = buf.getvalue()


@pytest.fixture
def client(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()

    @app.get("/api/outlet/{tenant_id}/exports/test")
    async def dummy_export(tenant_id: str):  # pragma: no cover - test helper
        return {"ok": True}

    from api.app import auth

    class DummyUser:
        role = "super_admin"

    app.dependency_overrides[auth.get_current_user] = lambda: DummyUser()

    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.pop(auth.get_current_user, None)


def _tenant_with_limits(limits):
    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    id = tenant_id
                    plan = "pro"
                    status = "active"
                    grace_until = None
                    license_limits = limits

                return _Tenant()

        yield _Session()

    return _session


def test_table_limit(client, monkeypatch):
    monkeypatch.setattr(
        lic_module, "get_session", _tenant_with_limits({"max_tables": 1})
    )

    async def _count(_):
        return 1

    monkeypatch.setattr(lic_module, "_table_count", _count)
    headers = {"X-Tenant-ID": "demo", "Authorization": "Bearer t"}
    resp = client.post("/api/outlet/demo/tables", headers=headers, json={"code": "T2"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FEATURE_LIMIT"


def test_menu_item_limit(client, monkeypatch):
    monkeypatch.setattr(
        lic_module, "get_session", _tenant_with_limits({"max_menu_items": 1})
    )

    async def _count(_):
        return 1

    monkeypatch.setattr(lic_module, "_menu_item_count", _count)
    headers = {"X-Tenant-ID": "demo", "Authorization": "Bearer t"}
    resp = client.post(
        "/api/outlet/demo/menu/items", headers=headers, json={"name": "Burger"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FEATURE_LIMIT"


def test_image_storage_limit(client, monkeypatch):
    monkeypatch.setattr(
        lic_module, "get_session", _tenant_with_limits({"max_images_mb": 1})
    )
    monkeypatch.setattr(lic_module, "storage_bytes", lambda tenant_id: 1024 * 1024)
    headers = {"X-Tenant-ID": "demo", "Authorization": "Bearer t"}
    resp = client.post(
        "/api/outlet/demo/media/upload",
        headers=headers,
        files={"file": ("tiny.png", PNG, "image/png")},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FEATURE_LIMIT"


def test_daily_export_limit(client, monkeypatch):
    monkeypatch.setattr(
        lic_module, "get_session", _tenant_with_limits({"max_daily_exports": 1})
    )
    url = "/api/outlet/demo/exports/test"
    headers = {"X-Tenant-ID": "demo", "Authorization": "Bearer t"}
    assert client.get(url, headers=headers).status_code == 200
    resp = client.get(url, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FEATURE_LIMIT"


def test_usage_endpoint(client, monkeypatch):
    limits = {
        "max_tables": 5,
        "max_menu_items": 10,
        "max_images_mb": 1,
        "max_daily_exports": 2,
    }
    monkeypatch.setattr(lic_module, "get_session", _tenant_with_limits(limits))

    async def _t(_):
        return 2

    async def _m(_):
        return 3

    monkeypatch.setattr(lic_module, "_table_count", _t)
    monkeypatch.setattr(lic_module, "_menu_item_count", _m)
    monkeypatch.setattr(lic_module, "storage_bytes", lambda tenant_id: 512 * 1024)
    app.state.redis = fakeredis.aioredis.FakeRedis()
    headers = {"X-Tenant-ID": "demo", "Authorization": "Bearer t"}
    resp = client.get("/api/outlet/demo/limits/usage", headers=headers)
    data = resp.json()["data"]
    assert data["tables"]["used"] == 2
    assert data["tables"]["limit"] == 5
    assert data["tables"]["remaining"] == 3
    assert data["menu_items"]["used"] == 3
    assert data["images_mb"]["used"] == 0.5
    assert data["images_mb"]["limit"] == 1
    assert data["images_mb"]["remaining"] == 0.5
    assert data["daily_exports"]["limit"] == 2
