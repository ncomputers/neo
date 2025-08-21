# test_tables.py
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import uuid

from fastapi.testclient import TestClient
import fakeredis.aioredis
import pytest

from api.app.main import SessionLocal, app
from api.app.models_tenant import Table
from api.app.auth import create_access_token
from api.app.deps import flags as flag_deps

client = TestClient(app)
HEADERS = {"X-Tenant-ID": "demo"}


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture(autouse=True)
def _enable_flags(monkeypatch):
    async def _can_use(tenant_id, flag):
        return True
    monkeypatch.setattr(flag_deps, "can_use", _can_use)


def test_cart_and_soft_cancel():
    item = {"item": "Tea", "price": 10.0, "quantity": 1}
    assert client.post("/tables/1/cart", json=item).status_code == 200
    client.post("/tables/1/order")
    resp = client.patch("/tables/1/order/0", json={"quantity": 0, "admin": True})
    assert resp.json()["data"]["orders"][0]["quantity"] == 0
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


def test_settlement_locks_and_cleaner_unlocks():
    table_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(Table(id=table_id, tenant_id=uuid.uuid4(), name="T1"))
        session.commit()

    item = {"item": "Tea", "price": 10.0, "quantity": 1}
    assert client.post(f"/tables/{table_id}/cart", json=item).status_code == 200
    client.post(f"/tables/{table_id}/order")
    client.post(f"/tables/{table_id}/pay")

    with SessionLocal() as session:
        table = session.get(Table, table_id)
        assert table.state == "LOCKED"

    # guests blocked while locked
    resp = client.post(f"/tables/{table_id}/cart", json=item)
    assert resp.status_code == 423
    assert resp.json()["error"]["code"] == "TABLE_LOCKED"

    token = create_access_token({"sub": "cleaner1", "role": "cleaner"})
    headers = {"Authorization": f"Bearer {token}"}
    headers_clean = {**headers, **HEADERS}
    resp = client.post(
        f"/api/outlet/demo/housekeeping/table/{table_id}/start_clean",
        headers=headers_clean,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "PENDING_CLEANING"
    resp = client.post(
        f"/api/outlet/demo/housekeeping/table/{table_id}/ready",
        headers=headers_clean,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "AVAILABLE"

    # table reopened
    assert client.post(f"/tables/{table_id}/cart", json=item).status_code == 200

