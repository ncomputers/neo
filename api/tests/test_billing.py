# test_billing.py
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def test_billing_flow_and_idempotency():
    item = {"item": "Tea", "price": 5.0, "quantity": 2}
    client.post("/tables/10/cart", json=item)
    client.post("/tables/10/order")
    assert client.get("/tables/10/bill").json()["data"]["total"] == 10.0
    assert client.post("/tables/10/pay").json()["data"]["total"] == 10.0
    # second pay should return zero
    assert client.post("/tables/10/pay").json()["data"]["total"] == 0.0


def test_bill_without_orders():
    assert client.get("/tables/99/bill").json()["data"]["total"] == 0.0
