import pathlib
import sys

from argon2 import PasswordHasher
import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app, SessionLocal
from api.app.models_tenant import Staff
from api.app.staff_auth import create_staff_token

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def seed_staff() -> int:
    ph = PasswordHasher()
    with SessionLocal() as session:
        staff = Staff(name="Alice", role="waiter", pin_hash=ph.hash("1234"))
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
        f"/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "1234"}
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    assert token
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/outlet/demo/staff/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "waiter"


def test_pin_throttle_and_reset():
    """After too many failures login is throttled until PIN reset."""
    staff_id = seed_staff()
    for _ in range(5):
        resp = client.post(
            f"/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "0000"}
        )
        assert resp.status_code == 400
    resp = client.post(
        f"/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "0000"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_THROTTLED"

    manager_id = seed_manager()
    token = create_staff_token(manager_id, "manager")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        f"/api/outlet/demo/staff/{staff_id}/set_pin",
        json={"pin": "4321"},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.post(
        f"/api/outlet/demo/staff/login", json={"code": staff_id, "pin": "4321"}
    )
    assert resp.status_code == 200
