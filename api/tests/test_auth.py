# test_auth.py
"""Tests for the in-memory authentication helpers."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from api.app import auth

app = FastAPI()


@app.get("/protected")
async def protected(user: auth.User = Depends(auth.role_required("admin"))):
    return {"user": user.username}


def test_authenticate_user_success_and_failure():
    assert auth.authenticate_user("admin@example.com", "adminpass")
    assert auth.authenticate_user("admin@example.com", "wrong") is None


def test_authenticate_pin_success_and_failure():
    assert auth.authenticate_pin("cashier1", "1234")
    assert auth.authenticate_pin("cashier1", "0000") is None


def test_create_access_token_and_get_current_user():
    token = auth.create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    user = auth.get_current_user(token)
    assert user.username == "admin@example.com"


def test_role_required_enforces():
    client = TestClient(app)
    token = auth.create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/protected", headers=headers)
    assert resp.status_code == 403
