# test_main.py
"""Tests for login and table billing endpoints."""

from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from api.app.main import app

client = TestClient(app)


def test_email_login_success_and_failure():
    assert client.post("/login/email", json={"username": "admin@example.com", "password": "adminpass"}).status_code == 200
    resp = client.post("/login/email", json={"username": "admin@example.com", "password": "wrong"})
    assert resp.status_code == 400


def test_pin_login_success_and_failure():
    assert client.post("/login/pin", json={"username": "cashier1", "pin": "1234"}).status_code == 200
    assert client.post("/login/pin", json={"username": "cashier1", "pin": "0000"}).status_code == 400


def test_table_flow_and_billing():
    item = {"item": "Coffee", "price": 5.0, "quantity": 1}
    assert client.post("/tables/1/cart", json=item).status_code == 200
    assert client.post("/tables/1/order").status_code == 200
    resp = client.patch("/tables/1/order/0", json={"quantity": 0, "admin": True})
    assert resp.status_code == 200
    # Ensure non-admin edit is rejected
    resp = client.patch("/tables/1/order/0", json={"quantity": 0, "admin": False})
    assert resp.status_code == 403
    resp = client.get("/tables/1/bill")
    assert resp.json()["total"] == 0
    resp = client.post("/tables/1/pay")
    assert resp.json()["total"] == 0
