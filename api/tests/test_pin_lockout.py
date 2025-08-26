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

from api.app.audit import Audit, SessionLocal
from api.app.auth import User
from api.app.main import app
from api.app.routes_admin_devices import unlock_pin
from api.app.security import blocklist

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def _clear_audit() -> None:
    with SessionLocal() as session:
        session.query(Audit).delete()
        session.commit()


def test_pin_lockout_and_unlock() -> None:
    _clear_audit()
    for _ in range(5):
        client.post("/login/pin", json={"username": "cashier1", "pin": "0000"})
    resp = client.post("/login/pin", json={"username": "cashier1", "pin": "1234"})
    assert resp.status_code == 403

    lock_key = "pin:lock:demo:cashier1:testclient"
    ttl = asyncio.get_event_loop().run_until_complete(app.state.redis.ttl(lock_key))
    assert ttl == 900
    with SessionLocal() as session:
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
    exists = asyncio.get_event_loop().run_until_complete(
        app.state.redis.exists(lock_key)
    )
    assert exists == 0

    with SessionLocal() as session:
        assert session.query(Audit).filter_by(action="pin_unlock").count() == 1

