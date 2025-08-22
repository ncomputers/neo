# test_tables_map.py
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import uuid
import asyncio
import json

import fakeredis.aioredis

from fastapi.testclient import TestClient
from api.app.main import app, SessionLocal
from api.app.models_tenant import Table
from api.app.auth import create_access_token
from api.app import routes_tables_map, routes_tables_sse

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


def test_table_map_stream_keepalive(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)
    monkeypatch.setattr(routes_tables_sse, "KEEPALIVE_INTERVAL", 0.01)

    async def run_stream():
        resp = await routes_tables_sse.stream_table_map("demo", None)
        first = await resp.body_iterator.__anext__()  # snapshot
        second = await resp.body_iterator.__anext__()  # keepalive
        await resp.body_iterator.aclose()
        return first, second

    snapshot, keepalive = asyncio.run(run_stream())
    snap_str = snapshot.decode() if isinstance(snapshot, bytes) else snapshot
    ka_str = keepalive.decode() if isinstance(keepalive, bytes) else keepalive
    assert snap_str.startswith("event: table_map")
    assert ka_str.startswith(":keepalive")


def test_table_map_stream_resume(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)

    async def initial():
        resp = await routes_tables_sse.stream_table_map("demo", None)
        await resp.body_iterator.__anext__()  # snapshot id 1
        await fake.publish(
            "rt:table_map:demo",
            json.dumps({"table_id": "t1", "code": "T1", "state": "LOCKED", "x": 1, "y": 2, "ts": 0}),
        )
        await asyncio.sleep(0)
        await resp.body_iterator.__anext__()  # diff id 2
        await resp.body_iterator.aclose()

    asyncio.run(initial())

    async def reconnect():
        resp = await routes_tables_sse.stream_table_map("demo", last_event_id="2")
        snap = await resp.body_iterator.__anext__()  # snapshot id 3
        await fake.publish(
            "rt:table_map:demo",
            json.dumps({"table_id": "t2", "code": "T2", "state": "BUSY", "x": 3, "y": 4, "ts": 1}),
        )
        await asyncio.sleep(0)
        while True:
            line = await resp.body_iterator.__anext__()
            line_str = line.decode() if isinstance(line, bytes) else line
            if "table_id" in line_str:
                diff = line
                break
        await resp.body_iterator.aclose()
        return snap, diff

    snap, diff = asyncio.run(reconnect())
    snap_str = snap.decode() if isinstance(snap, bytes) else snap
    diff_str = diff.decode() if isinstance(diff, bytes) else diff
    assert "id: 3" in snap_str and "event: table_map" in snap_str
    assert "id: 4" in diff_str and "table_id" in diff_str
