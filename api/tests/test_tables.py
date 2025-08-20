# test_tables.py
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from api.app.main import app

client = TestClient(app)


def test_cart_and_soft_cancel():
    item = {"item": "Tea", "price": 10.0, "quantity": 1}
    assert client.post("/tables/1/cart", json=item).status_code == 200
    client.post("/tables/1/order")
    resp = client.patch("/tables/1/order/0", json={"quantity": 0, "admin": True})
    assert resp.json()["orders"][0]["quantity"] == 0
    assert (
        client.patch(
            "/tables/1/order/0", json={"quantity": 0, "admin": False}
        ).status_code
        == 403
    )


def test_update_order_invalid_index():
    assert (
        client.patch(
            "/tables/2/order/5", json={"quantity": 0, "admin": True}
        ).status_code
        == 404
    )
