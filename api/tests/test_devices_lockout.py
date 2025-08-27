import asyncio
import os
import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient
from starlette.requests import Request

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "*")

from api.app.audit import Audit
from api.app.audit import SessionLocal as AuditSession
from api.app.auth import User, UserInDB, create_access_token, fake_users_db
from api.app.db import SessionLocal as DBSession
from api.app.main import PinLogin, app, pin_login
from api.app.models_master import Device
from api.app.routes_admin_devices import unlock_pin
from api.app.security import blocklist
from api.app.utils.audit import AuditTenant

client = TestClient(app)


def setup_module() -> None:
    """Initialize Redis and clear persistent state."""
    app.state.redis = fakeredis.aioredis.FakeRedis()
    fake_users_db["manager1"] = UserInDB(
        username="manager1", role="manager", password_hash=""
    )
    with DBSession() as session:
        session.query(Device).delete()
        session.query(AuditTenant).delete()
        session.commit()
    with AuditSession() as session:
        session.query(Audit).delete()
        session.commit()


def test_device_register_pin_lockout() -> None:
    """End-to-end device registration and PIN lockout flow."""
    admin = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    manager = create_access_token({"sub": "manager1", "role": "manager"})
    cashier = create_access_token({"sub": "cashier1", "role": "cashier"})

    fingerprint = "locktest"
    resp = client.post(
        "/admin/devices/register",
        json={"name": "TabLock", "fingerprint": fingerprint},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 200

    resp = client.get(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 200
    assert any(d["fingerprint"] == fingerprint for d in resp.json()["data"])

    resp = client.get(
        "/admin/devices",
        headers={"Authorization": f"Bearer {cashier}"},
    )
    assert resp.status_code == 403

    with DBSession() as session:
        assert (
            session.query(AuditTenant).filter_by(action="devices.register").count() == 1
        )

    for _ in range(5):
        client.post("/login/pin", json={"username": "cashier1", "pin": "0000"})

    r = client.post("/login/pin", json={"username": "cashier1", "pin": "1234"})
    assert r.status_code == 403

    lock_key = "pin:lock:demo:cashier1:testclient"
    ttl = asyncio.get_event_loop().run_until_complete(app.state.redis.ttl(lock_key))
    assert ttl == 900

    with AuditSession() as session:
        assert session.query(Audit).filter_by(action="pin_lock").count() == 1
    req = Request(
        {
            "type": "http",
            "app": app,
            "headers": [],
            "path": "/admin/staff/cashier1/unlock_pin",
        }
    )
    asyncio.get_event_loop().run_until_complete(
        unlock_pin("cashier1", req, User(username="manager1", role="manager"))
    )
    asyncio.get_event_loop().run_until_complete(
        blocklist.clear_ip(app.state.redis, "demo", "testclient")
    )

    with AuditSession() as session:
        assert session.query(Audit).filter_by(action="pin_unlock").count() == 1

    result = asyncio.get_event_loop().run_until_complete(
        pin_login(PinLogin(username="cashier1", pin="1234"))
    )
    assert result["ok"] is True
