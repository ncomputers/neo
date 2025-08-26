import pathlib
import sys
from datetime import datetime, timedelta
import os

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))  # noqa: E402

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

from api.app.audit import Audit  # noqa: E402
from api.app.audit import SessionLocal as AuditSession  # noqa: E402
from api.app.main import SessionLocal, app  # noqa: E402
from api.app.models_tenant import AuditTenant, Staff  # noqa: E402
from api.app.staff_auth import create_staff_token  # noqa: E402
from tests.conftest import DummyRedis

client = TestClient(app)


def setup_module():
    app.state.redis = DummyRedis()


def seed_staff(pin_set_at: datetime | None = None) -> int:
    ph = PasswordHasher()
    with SessionLocal() as session:
        staff = Staff(
            name="Alice",
            role="waiter",
            pin_hash=ph.hash("1234"),
            pin_set_at=pin_set_at or datetime.utcnow(),
        )
        session.add(staff)
        session.commit()
        return staff.id


def seed_manager() -> int:
    """Insert a manager for authorization tests."""
    ph = PasswordHasher()
    with SessionLocal() as session:
        staff = Staff(name="Bob", role="manager", pin_hash=ph.hash("9999"))
        session.add(staff)
        session.commit()
        return staff.id


def test_staff_pin_login_happy_path():
    """Waiter can log in with PIN and retrieve their role."""
    staff_id = seed_staff()
    resp = client.post(
        "/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "1234"}
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    assert token
    assert resp.json()["data"].get("rotation_warning") is None
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/outlet/demo/staff/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "waiter"


def test_pin_lockout_and_reset():
    """After too many failures login is locked until PIN reset."""
    staff_id = seed_staff()
    for _ in range(4):
        resp = client.post(
            "/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "0000"}
        )
        assert resp.status_code == 400
    resp = client.post(
        "/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "0000"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_LOCKED"


    manager_id = seed_manager()
    token = create_staff_token(manager_id, "manager")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        f"/api/outlet/demo/staff/{staff_id}/set_pin",
        json={"pin": "4321"},
        headers=headers,
    )
    assert resp.status_code == 200

    with SessionLocal() as session:
        row = session.query(AuditTenant).filter_by(action="set_pin").first()
        assert row is not None
        assert row.actor == f"{manager_id}:manager"
        assert row.meta["target"]["staff_id"] == str(staff_id)


    resp = client.post(
        "/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "4321"}
    )
    assert resp.status_code == 200


def test_pin_rotation_policy():
    """Warn at 80 days and reject after 90 days."""
    warn_id = seed_staff(pin_set_at=datetime.utcnow() - timedelta(days=85))
    resp = client.post(
        "/api/outlet/demo/staff/login", json={"code": warn_id, "pin": "1234"}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rotation_warning"] is True

    expire_id = seed_staff(pin_set_at=datetime.utcnow() - timedelta(days=91))
    resp = client.post(
        "/api/outlet/demo/staff/login", json={"code": expire_id, "pin": "1234"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["message"] == "PIN expired"
