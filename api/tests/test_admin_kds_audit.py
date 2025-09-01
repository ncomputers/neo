import pathlib
import sys
import uuid

import fakeredis.aioredis
import pytest
from argon2 import PasswordHasher
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app, SessionLocal
from api.app.models_tenant import AuditTenant, Staff, Table, TableStatus
from api.app.staff_auth import create_staff_token
from api.app.auth import create_access_token
from api.app import routes_admin_menu, routes_housekeeping, routes_counter, routes_alerts
from api.app.repos_sqlalchemy import menu_repo_sql, counter_orders_repo_sql

client = TestClient(app)


def _clear_audit():
    with SessionLocal() as session:
        session.query(AuditTenant).delete()
        session.commit()


@pytest.mark.parametrize(
    "caller, action, target_key",
    [
        ("_call_set_pin", "set_pin", "staff_id"),
        ("_call_out_of_stock", "toggle_out_of_stock", "item_id"),
        ("_call_start_clean", "start_clean_table", "table_id"),
        ("_call_counter_status", "update_counter_status", "order_id"),
        ("_call_create_rule", "create_alert_rule", None),
    ],
)
def test_audit_logged(monkeypatch, caller, action, target_key):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    actor, target = globals()[caller](monkeypatch)
    with SessionLocal() as session:
        row = session.query(AuditTenant).filter_by(action=action).first()
        assert row is not None
        assert row.actor == actor
        if target_key is not None:
            assert row.meta["target"][target_key] == target
    _clear_audit()


def _call_set_pin(monkeypatch):
    ph = PasswordHasher()
    with SessionLocal() as session:
        staff = Staff(name="Alice", role="waiter", pin_hash=ph.hash("1234"))
        manager = Staff(name="Bob", role="manager", pin_hash=ph.hash("9999"))
        session.add_all([staff, manager])
        session.commit()
        staff_id = staff.id
        manager_id = manager.id
    token = create_staff_token(manager_id, "manager")
    resp = client.post(
        f"/api/outlet/demo/staff/{staff_id}/set_pin",
        json={"pin": "4321"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return f"{manager_id}:manager", str(staff_id)


def _call_out_of_stock(monkeypatch):
    item_id = str(uuid.uuid4())

    @asynccontextmanager
    async def fake_session(tenant_id):
        class Dummy:
            pass
        yield Dummy()

    async def fake_toggle(self, session, item_id, flag):
        return None

    async def fake_list_items(self, session, include_hidden=False, include_deleted=False):
        return []

    monkeypatch.setattr(routes_admin_menu, "_session", fake_session)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "toggle_out_of_stock", fake_toggle)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", fake_list_items)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    resp = client.post(
        f"/api/outlet/demo/menu/item/{item_id}/out_of_stock",
        json={"flag": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return "admin@example.com:super_admin", item_id


def _call_start_clean(monkeypatch):
    table_id = str(uuid.uuid4())
    with SessionLocal() as session:
        code = uuid.uuid4().hex[:6]
        table = Table(
            id=uuid.UUID(table_id),
            tenant_id=uuid.uuid4(),
            name="T1",
            code=code,
            qr_token=code,
            status=TableStatus.AVAILABLE,
            state="AVAILABLE",
        )
        session.add(table)
        session.commit()

    async def fake_publish(table):
        return None

    monkeypatch.setattr(routes_housekeeping, "publish_table_state", fake_publish)

    token = create_access_token({"sub": "cleaner1", "role": "cleaner"})
    resp = client.post(
        f"/api/outlet/demo/housekeeping/table/{table_id}/start_clean",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return "cleaner1:cleaner", table_id


def _call_counter_status(monkeypatch):
    async def fake_session(tenant_id):
        class Dummy:
            pass
        yield Dummy()

    async def fake_update(session, order_id, status):
        return 1

    monkeypatch.setattr(routes_counter, "get_session_from_path", fake_session)
    monkeypatch.setattr(counter_orders_repo_sql, "update_status", fake_update)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    resp = client.post(
        "/api/outlet/demo/counters/1/status",
        json={"status": "ready"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return "admin@example.com:super_admin", "1"


def _call_create_rule(monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id):
        class Dummy:
            def add(self, obj):
                obj.id = 1
            async def commit(self):
                return None
        yield Dummy()

    monkeypatch.setattr(routes_alerts, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    resp = client.post(
        "/api/outlet/demo/alerts/rules",
        json={"event": "x", "channel": "sms", "target": "z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return "admin@example.com:super_admin", None
