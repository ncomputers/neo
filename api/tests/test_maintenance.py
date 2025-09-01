from __future__ import annotations

import os
import pathlib
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
from api.app import main as app_main  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.middlewares import maintenance as maint_module  # noqa: E402
from api.app.models_master import Tenant  # noqa: E402
from api.app.models_tenant import AuditTenant  # noqa: E402


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


def _admin_token(client: TestClient) -> str:
    resp = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "adminpass"},
    )
    return resp.json()["data"]["access_token"]


def test_global_maintenance(client, monkeypatch):
    token = _admin_token(client)
    monkeypatch.setenv("MAINTENANCE", "1")

    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["code"] == "MAINTENANCE"

    resp = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_tenant_maintenance(client, monkeypatch):
    token = _admin_token(client)

    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tenant_id):
                class _Tenant:
                    maintenance_until = datetime.utcnow() + timedelta(minutes=5)

                return _Tenant()

        yield _Session()

    monkeypatch.delenv("MAINTENANCE", raising=False)
    monkeypatch.setattr(maint_module, "get_session", _session)

    resp = client.get("/version", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 503
    assert resp.json()["code"] == "MAINTENANCE"
    assert resp.headers["Retry-After"].isdigit()

    resp = client.get(
        "/admin",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "demo",
        },
    )
    assert resp.status_code == 200


def test_schedule_maintenance(client):
    token = _admin_token(client)
    tenant_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(Tenant(id=tenant_id, name="Demo", status="active"))
        session.commit()

    until = datetime.utcnow() + timedelta(minutes=30)
    resp = client.post(
        f"/api/outlet/{tenant_id}/maintenance/schedule",
        headers={"Authorization": f"Bearer {token}"},
        json={"until": until.isoformat(), "note": "upgrade"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["maintenance_until"]  # type: ignore[index]
    returned = datetime.fromisoformat(data)
    assert returned == until.replace(tzinfo=None)

    with SessionLocal() as session:
        tenant = session.get(Tenant, tenant_id)
        assert tenant is not None and tenant.maintenance_until == until.replace(
            tzinfo=None
        )
        row = (
            session.query(AuditTenant).filter_by(action="schedule_maintenance").first()
        )
        assert row is not None


def test_close_blocks_guest(client, monkeypatch):
    token = _admin_token(client)
    tenant_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(Tenant(id=tenant_id, name="CloseDemo", status="active"))
        session.commit()

    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tid):
                with SessionLocal() as s:
                    return s.get(model, uuid.UUID(str(tid)))

        yield _Session()

    monkeypatch.setattr(maint_module, "get_session", _session)

    resp = client.post(
        f"/api/outlet/{tenant_id}/close",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    resp = client.get("/version", headers={"X-Tenant-ID": str(tenant_id)})
    assert resp.status_code == 403
    assert resp.json()["code"] == "TENANT_CLOSED"

    resp_menu = client.get("/guest/foo", headers={"X-Tenant-ID": str(tenant_id)})
    assert resp_menu.status_code != 403

    item = {"item": "tea", "price": 2.0, "quantity": 1}
    resp_cart = client.post(
        "/tables/10/cart",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=item,
    )
    assert resp_cart.status_code == 403
    assert resp_cart.json()["code"] == "TENANT_CLOSED"


def test_restore_reopens(client, monkeypatch):
    token = _admin_token(client)
    tenant_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(Tenant(id=tenant_id, name="RestoreDemo", status="active"))
        session.commit()

    @asynccontextmanager
    async def _session():
        class _Session:
            async def get(self, model, tid):
                with SessionLocal() as s:
                    return s.get(model, uuid.UUID(str(tid)))

        yield _Session()

    monkeypatch.setattr(maint_module, "get_session", _session)

    client.post(
        f"/api/outlet/{tenant_id}/close",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.post(
        f"/api/admin/tenants/{tenant_id}/restore",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    resp = client.get("/version", headers={"X-Tenant-ID": str(tenant_id)})
    assert resp.status_code == 200
