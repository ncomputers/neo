from argon2 import PasswordHasher
import fakeredis.aioredis
from fastapi.testclient import TestClient

from api.app.main import app, SessionLocal
from api.app.models_tenant import Staff

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
