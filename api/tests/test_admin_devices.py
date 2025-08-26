import os
import pathlib
import sys

from fastapi.testclient import TestClient
import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "*")

from api.app.auth import create_access_token
from api.app.db import SessionLocal
from api.app.models_master import Device
from api.app.main import app

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    with SessionLocal() as session:
        session.query(Device).delete()
        session.commit()


def test_device_rbac() -> None:
    admin = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    cashier = create_access_token({"sub": "cashier1", "role": "cashier"})

    resp = client.post(
        "/admin/devices/register",
        json={"name": "Tab1", "fingerprint": "abc"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 200

    resp = client.get(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["name"] == "Tab1"

    resp = client.post(
        "/admin/devices/register",
        json={"name": "Tab2", "fingerprint": "def"},
        headers={"Authorization": f"Bearer {cashier}"},
    )
    assert resp.status_code == 403
