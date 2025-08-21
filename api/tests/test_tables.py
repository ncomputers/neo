# test_tables.py
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import uuid

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import SessionLocal, app
from api.app.models_tenant import Table, TableStatus

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


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


def test_lock_and_clean_persist():
    table_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(Table(id=table_id, tenant_id=uuid.uuid4(), name="T1"))
        session.commit()

    resp = client.post(f"/tables/{table_id}/lock")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == TableStatus.LOCKED.value

    resp = client.post(f"/tables/{table_id}/mark-clean")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == TableStatus.AVAILABLE.value

    with SessionLocal() as session:
        table = session.get(Table, table_id)
        assert table.status == TableStatus.AVAILABLE


def test_table_map_positions():
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    with SessionLocal() as session:
        session.add(Table(id=t1, tenant_id=uuid.uuid4(), name="T1", code="T1"))
        session.add(
            Table(
                id=t2,
                tenant_id=uuid.uuid4(),
                name="T2",
                code="T2",
                status=TableStatus.OCCUPIED,
            )
        )
        session.commit()

    client.post(
        f"/api/outlet/demo/tables/{t1}/position",
        json={"x": 10, "y": 20, "label": "A1"},
    )
    client.post(
        f"/api/outlet/demo/tables/{t2}/position",
        json={"x": 30, "y": 40},
    )

    resp = client.get("/api/outlet/demo/tables/map")
    assert resp.status_code == 200
    data = {entry["code"]: entry for entry in resp.json()["data"]}
    assert data["T1"] == {
        "id": str(t1),
        "code": "T1",
        "label": "A1",
        "x": 10,
        "y": 20,
        "state": TableStatus.AVAILABLE.value,
    }
    assert data["T2"] == {
        "id": str(t2),
        "code": "T2",
        "label": None,
        "x": 30,
        "y": 40,
        "state": TableStatus.OCCUPIED.value,
    }
