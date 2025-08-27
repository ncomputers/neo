"""Tests for L1 support console endpoints."""

import pathlib
import sys
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.routes_support_console import router
from api.app.auth import create_access_token
from api.app.models_master import Tenant
from api.app.models_tenant import AuditTenant, Order, OrderStatus, Staff, Table

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class FakeSession:
    def __init__(self):
        self.tenant_id = uuid.uuid4()
        self.tenant = Tenant(id=self.tenant_id, name="t1")
        self.table = Table(id=uuid.uuid4(), tenant_id=self.tenant_id, name="T1", code="T1")
        self.order = Order(id=1, table_id=1, status=OrderStatus.READY)
        self.staff = Staff(id=1, name="alice", role="waiter", pin_hash="x")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, model, key):
        if model is Tenant and key == self.tenant_id:
            return self.tenant
        if model is Order and key == self.order.id:
            return self.order
        if model is Table and key == uuid.UUID(int=self.order.table_id):
            return self.table
        if model is Staff and key == self.staff.id:
            return self.staff
        return None

    def query(self, model):
        class Q:
            def __init__(self, table):
                self.table = table

            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return self.table

        return Q(self.table)

    def add(self, obj):
        pass

    def commit(self):
        pass


class AuditSession:
    def __init__(self, log: list[AuditTenant]):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def add(self, obj):
        self.log.append(obj)

    def commit(self):
        pass


def _token(role: str = "super_admin") -> str:
    return create_access_token({"sub": "admin@example.com", "role": role})


def _non_super_token() -> str:
    return create_access_token({"sub": "owner@example.com", "role": "owner"})


def test_support_console_audit() -> None:
    fake_session = FakeSession()
    audit_log: list[AuditTenant] = []
    app.state.redis = fakeredis.aioredis.FakeRedis()
    mock_enqueue = AsyncMock()
    app.state.redis.publish = AsyncMock()
    with (
        patch("api.app.routes_support_console.SessionLocal", lambda: fake_session),
        patch("api.app.utils.audit.SessionLocal", lambda: AuditSession(audit_log)),
        patch("api.app.routes_support_console.notifications.enqueue", mock_enqueue),
    ):
        token = _token()
        tenant_id = str(fake_session.tenant_id)
        resp = client.get(
            f"/admin/support/console/search?tenant={tenant_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        order_id = fake_session.order.id
        resp = client.post(
            f"/admin/support/console/order/{order_id}/resend_invoice",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        resp = client.post(
            f"/admin/support/console/order/{order_id}/reprint_kot",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        resp = client.post(
            f"/admin/support/console/order/{order_id}/replay_webhook",
            headers={"Authorization": f"Bearer {token}"},
            params={"confirm": "true"},
        )
        assert resp.status_code == 200
        resp = client.post(
            "/admin/support/console/staff/1/unlock_pin",
            headers={"Authorization": f"Bearer {token}"},
            params={"confirm": "true"},
        )
        assert resp.status_code == 200
    assert mock_enqueue.await_count == 2
    assert {a.action for a in audit_log} == {
        "support.console.search",
        "support.console.resend_invoice",
        "support.console.reprint_kot",
        "support.console.replay_webhook",
        "support.console.unlock_pin",
    }


def test_support_console_forbidden() -> None:
    fake_session = FakeSession()
    audit_log: list[AuditTenant] = []
    with (
        patch("api.app.routes_support_console.SessionLocal", lambda: fake_session),
        patch("api.app.utils.audit.SessionLocal", lambda: AuditSession(audit_log)),
    ):
        token = _non_super_token()
        tenant_id = str(fake_session.tenant_id)
        endpoints = [
            f"/admin/support/console/search?tenant={tenant_id}",
            "/admin/support/console/order/1/resend_invoice",
            "/admin/support/console/order/1/reprint_kot",
            "/admin/support/console/order/1/replay_webhook?confirm=true",
            "/admin/support/console/staff/1/unlock_pin?confirm=true",
        ]
        for path in endpoints:
            resp = (
                client.get(path, headers={"Authorization": f"Bearer {token}"})
                if path.endswith("search?tenant=" + tenant_id)
                else client.post(path, headers={"Authorization": f"Bearer {token}"})
            )
            assert resp.status_code == 403
    assert audit_log == []
