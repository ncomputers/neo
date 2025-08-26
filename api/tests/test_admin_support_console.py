"""Tests for L1 support console endpoints."""

import pathlib
import sys
import uuid
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.routes_admin_support_console import router
from api.app.auth import create_access_token
from api.app.db import SessionLocal
from api.app.models_master import Tenant
from api.app.models_tenant import (
    AuditTenant,
    Order,
    OrderStatus,
    Staff,
    Table,
)


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _token(role: str = "super_admin") -> str:
    return create_access_token({"sub": "admin@example.com", "role": role})


def _non_super_token() -> str:
    return create_access_token({"sub": "owner@example.com", "role": "owner"})


def _seed() -> tuple[str, int]:
    tenant_uuid = uuid.uuid4()
    table_uuid = uuid.UUID(int=1)
    with SessionLocal() as session:
        session.query(AuditTenant).delete()
        session.query(Order).delete()
        session.query(Table).delete()
        session.query(Tenant).delete()
        session.query(Staff).delete()
        session.commit()
        session.add(Tenant(id=tenant_uuid, name="t1"))
        session.add(Table(id=table_uuid, tenant_id=tenant_uuid, name="T1", code="T1"))
        session.add(Order(id=1, table_id=1, status=OrderStatus.READY))
        session.add(Staff(id=1, name="alice", role="waiter", pin_hash="x"))
        session.commit()
    return str(tenant_uuid), 1


def test_support_console_audit() -> None:
    tenant_id, order_id = _seed()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    mock_enqueue = AsyncMock()
    app.state.redis.publish = AsyncMock()
    with patch(
        "api.app.routes_admin_support_console.notifications.enqueue",
        mock_enqueue,
    ):
        token = _token()
        resp = client.get(
            f"/admin/support/console/search?tenant={tenant_id}&table=T1&order={order_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        paths = [
            f"/admin/support/console/order/{order_id}/resend_invoice",
            f"/admin/support/console/order/{order_id}/reprint_kot",
            f"/admin/support/console/order/{order_id}/replay_webhook",
            "/admin/support/console/staff/1/unlock_pin",
        ]
        for p in paths:
            resp = client.post(p, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
    assert mock_enqueue.await_count == 2
    mock_enqueue.assert_any_await(tenant_id, "invoice.resend", {"order_id": order_id})
    mock_enqueue.assert_any_await(tenant_id, "webhook.replay", {"order_id": order_id})
    assert app.state.redis.publish.await_count == 1
    with SessionLocal() as session:
        actions = {r.action for r in session.query(AuditTenant).all()}
    assert actions == {
        "support.console.search",
        "support.console.resend_invoice",
        "support.console.reprint_kot",
        "support.console.replay_webhook",
        "support.console.unlock_pin",
    }


def test_support_console_forbidden() -> None:
    token = _non_super_token()
    tenant_id, _ = _seed()
    endpoints = [
        f"/admin/support/console/search?tenant={tenant_id}",
        "/admin/support/console/order/1/resend_invoice",
        "/admin/support/console/order/1/reprint_kot",
        "/admin/support/console/order/1/replay_webhook",
        "/admin/support/console/staff/1/unlock_pin",
    ]
    for path in endpoints:
        resp = (
            client.get(path, headers={"Authorization": f"Bearer {token}"})
            if path.endswith("search?tenant=" + tenant_id)
            else client.post(path, headers={"Authorization": f"Bearer {token}"})
        )
        assert resp.status_code == 403
    with SessionLocal() as session:
        assert session.query(AuditTenant).count() == 0


def test_search_tenant_scoping() -> None:
    tenant_id, _ = _seed()
    other_uuid = uuid.uuid4()
    other_table = uuid.UUID(int=2)
    with SessionLocal() as session:
        session.add(Tenant(id=other_uuid, name="t2"))
        session.add(Table(id=other_table, tenant_id=other_uuid, name="T2", code="T2"))
        session.add(Order(id=2, table_id=2, status=OrderStatus.READY))
        session.commit()
    token = _token()
    resp = client.get(
        f"/admin/support/console/search?tenant={tenant_id}&table=T1&order=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()["data"]
    assert data["tenant"]["id"] == tenant_id
    assert data["table"]["code"] == "T1"
    assert data["order"]["id"] == 1

    resp = client.get(
        f"/admin/support/console/search?tenant={tenant_id}&table=T2&order=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert "table" not in resp.json()["data"]
    assert "order" not in resp.json()["data"]

    resp = client.get(
        f"/admin/support/console/search?tenant={uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_unlock_pin_missing_staff() -> None:
    _seed()
    token = _token()
    resp = client.post(
        "/admin/support/console/staff/999/unlock_pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    with SessionLocal() as session:
        assert session.query(AuditTenant).count() == 0
