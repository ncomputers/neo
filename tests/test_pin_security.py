import time
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from api.app.audit import Audit, SessionLocal
from api.app.main import app
from api.app.middlewares import pin_security
from tests.conftest import DummyRedis

client = TestClient(app)


def _clear_audit():
    with SessionLocal() as session:
        session.query(Audit).delete()
        session.commit()


def _redis():
    app.state.redis = DummyRedis()
    return app.state.redis


def test_pin_lock_after_failed_attempts():
    _clear_audit()
    r = _redis()
    payload = {"username": "cashier1", "pin": "0000"}
    for _ in range(5):
        res = client.post("/login/pin", json=payload)
        assert res.status_code == 400
    res = client.post("/login/pin", json=payload)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_LOCKED"


def test_pin_unlock_after_ttl(monkeypatch):
    _clear_audit()
    r = _redis()
    monkeypatch.setattr(pin_security, "LOCK_TTL", 1)
    bad = {"username": "cashier1", "pin": "0000"}
    good = {"username": "cashier1", "pin": "1234"}
    for _ in range(5):
        client.post("/login/pin", json=bad)
    assert client.post("/login/pin", json=bad).status_code == 403
    time.sleep(1.2)
    res = client.post("/login/pin", json=good)
    assert res.status_code == 200


def test_pin_rotation_enforced():
    _clear_audit()
    r = _redis()
    past = (datetime.utcnow() - timedelta(days=91)).isoformat()
    r.store[f"pin:rot:demo:cashier1"] = (past, None)
    res = client.post("/login/pin", json={"username": "cashier1", "pin": "1234"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PIN_EXPIRED"
