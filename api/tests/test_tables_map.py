# test_tables_map.py
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import uuid

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app, SessionLocal
from api.app.models_tenant import Table
from api.app.auth import create_access_token

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def test_table_positions_map():
    tid1, tid2 = uuid.uuid4(), uuid.uuid4()
    with SessionLocal() as session:
        session.add_all(
            [
                Table(
                    id=tid1,
                    tenant_id=uuid.uuid4(),
                    name="T1",
                    code="T1",
                    state="AVAILABLE",
                ),
                Table(
                    id=tid2,
                    tenant_id=uuid.uuid4(),
                    name="T2",
                    code="T2",
                    state="LOCKED",
                ),
            ]
        )
        session.commit()

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(
            f"/api/outlet/demo/tables/{tid1}/position",
            json={"x": 10, "y": 20, "label": "A"},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/outlet/demo/tables/{tid2}/position",
            json={"x": 30, "y": 40},
            headers=headers,
        ).status_code
        == 200
    )

    resp = client.get("/api/outlet/demo/tables/map")
    assert resp.status_code == 200
    data = resp.json()["data"]

    m1 = next(item for item in data if item["id"] == str(tid1))
    assert m1 == {
        "id": str(tid1),
        "code": "T1",
        "label": "A",
        "x": 10,
        "y": 20,
        "state": "AVAILABLE",
    }

    m2 = next(item for item in data if item["id"] == str(tid2))
    assert m2 == {
        "id": str(tid2),
        "code": "T2",
        "label": None,
        "x": 30,
        "y": 40,
        "state": "LOCKED",
    }
