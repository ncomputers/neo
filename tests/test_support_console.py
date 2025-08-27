"""Tests for L1 support console."""

import pathlib
import sys
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis.aioredis

# ensure repo root on path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

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


def test_console_page_html_admin() -> None:
    token = _token()
    resp = client.get(
        "/admin/support/console",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    for label in [
        "Resend Invoice",
        "Reprint KOT",
        "Replay Webhook",
        "Unlock PIN",
    ]:
        assert label in resp.text


def test_console_page_non_admin() -> None:
    token = _non_super_token()
    resp = client.get(
        "/admin/support/console",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 200:
        assert "permission" in resp.text.lower()
    else:
        assert resp.status_code == 403


@pytest.mark.parametrize(
    "path,action",
    [
        ("/admin/support/console/order/1/resend_invoice", "support.console.resend_invoice"),
        ("/admin/support/console/order/1/reprint_kot", "support.console.reprint_kot"),
        (
            "/admin/support/console/order/1/replay_webhook?confirm=true",
            "support.console.replay_webhook",
        ),
        (
            "/admin/support/console/staff/1/unlock_pin?confirm=true",
            "support.console.unlock_pin",
        ),
    ],
)
def test_support_console_actions_audit(path: str, action: str) -> None:
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
        resp = client.post(
            path, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
    assert any(a.action == action for a in audit_log)


def test_support_console_search_audit() -> None:
    fake_session = FakeSession()
    audit_log: list[AuditTenant] = []
    with (
        patch("api.app.routes_support_console.SessionLocal", lambda: fake_session),
        patch("api.app.utils.audit.SessionLocal", lambda: AuditSession(audit_log)),
    ):
        token = _token()
        tenant_id = str(fake_session.tenant_id)
        resp = client.get(
            f"/admin/support/console/search?tenant={tenant_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
    assert any(a.action == "support.console.search" for a in audit_log)
