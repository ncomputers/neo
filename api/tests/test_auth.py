# test_auth.py
import pathlib
import sys
from datetime import timedelta

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from jose import JWTError, jwt

from api.app.auth import ALGORITHM, SECRET_KEY, create_access_token
from api.app.main import app

client = TestClient(app)


def test_password_login_success():
    resp = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "adminpass"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


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
    try:
        jwt.decode(expired, SECRET_KEY, algorithms=[ALGORITHM])
        assert False
    except JWTError:
        pass


def test_role_enforcement_allow_and_deny():
    admin_token = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "adminpass"},
    ).json()["access_token"]
    cashier_token = client.post(
        "/login/email",
        json={"username": "cashier1", "password": "cashierpass"},
    ).json()["access_token"]
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
