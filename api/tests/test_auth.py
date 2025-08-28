# test_auth.py
import pathlib
import sys
from datetime import timedelta

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import os

import fakeredis.aioredis
import jwt
import pytest
from argon2.exceptions import VerificationError
from fastapi.testclient import TestClient

os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import api.app.auth as auth
from api.app.auth import ALGORITHM, SECRET_KEY, create_access_token, ph, verify_password
from api.app.main import app

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def test_password_login_success():
    resp = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "adminpass"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


def test_password_login_fail():
    resp = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "wrong"},
    )
    assert resp.status_code == 400


def test_pin_login_success():
    resp = client.post("/login/pin", json={"username": "cashier1", "pin": "1234"})
    assert resp.status_code == 200


def test_pin_login_fail():
    resp = client.post("/login/pin", json={"username": "cashier1", "pin": "0000"})
    assert resp.status_code == 400


def test_jwt_claims_and_expiry():
    token = create_access_token(
        {"sub": "u", "role": "r"}, expires_delta=timedelta(seconds=60)
    )
    data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert data["sub"] == "u"
    expired = create_access_token(
        {"sub": "u", "role": "r"}, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(expired, SECRET_KEY, algorithms=[ALGORITHM])


def test_role_enforcement_allow_and_deny():
    admin_token = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "adminpass"},
    ).json()["data"]["access_token"]
    cashier_token = client.post(
        "/login/email",
        json={"username": "cashier1", "password": "cashierpass"},
    ).json()["data"]["access_token"]
    assert (
        client.get(
            "/admin", headers={"Authorization": f"Bearer {admin_token}"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/admin", headers={"Authorization": f"Bearer {cashier_token}"}
        ).status_code
        == 403
    )


def test_verify_password_incorrect():
    hashed = ph.hash("secret")
    assert verify_password("wrong", hashed) is False


def test_verify_password_unexpected_error(monkeypatch):
    class Dummy:
        def verify(self, *args, **kwargs):
            raise VerificationError("boom")

    monkeypatch.setattr(auth, "ph", Dummy())
    with pytest.raises(VerificationError):
        verify_password("a", "b")
