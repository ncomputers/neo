import asyncio
import json
import os
import pathlib
import sys
import uuid

import fakeredis.aioredis
from fastapi.testclient import TestClient

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import routes_floor
from api.app.auth import create_access_token
from api.app.main import SessionLocal, app
from api.app.models_tenant import Table

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def test_floor_map_save_rbac():
    token = create_access_token({"sub": "owner@example.com", "role": "owner"})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/admin/floor-map/save", json={"tables": []}, headers=headers)
    assert resp.status_code == 403


def test_floor_map_save_roundtrip():
    tid = uuid.uuid4()
    with SessionLocal() as session:
        session.add(
            Table(
                id=tid,
                tenant_id=uuid.uuid4(),
                name="T1",
                code="T1",
                state="AVAILABLE",
            )
        )
        session.commit()
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "tables": [
            {
                "id": str(tid),
                "pos_x": 10,
                "pos_y": 20,
                "width": 90,
                "height": 100,
                "shape": "rect",
                "zone": "A",
                "capacity": 4,
                "label": "T1",
            }
        ]
    }
    resp = client.post("/admin/floor-map/save", json=payload, headers=headers)
    assert resp.status_code == 200
    with SessionLocal() as session:
        tbl = session.get(Table, tid)
        assert tbl.pos_x == 10 and tbl.pos_y == 20
        assert tbl.width == 90 and tbl.height == 100
        assert tbl.zone == "A" and tbl.capacity == 4
        assert tbl.label == "T1"


def test_floor_stream_update(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)

    async def run():
        resp = await routes_floor.floor_stream("demo")
        await resp.body_iterator.__anext__()  # snapshot
        await fake.publish(
            "rt:table_map:demo",
            json.dumps({"table_id": "t1", "state": "BUSY", "x": 1, "y": 2}),
        )
        await asyncio.sleep(0)
        while True:
            line = await asyncio.wait_for(resp.body_iterator.__anext__(), timeout=2)
            text = line.decode() if isinstance(line, bytes) else line
            if "table_id" in text:
                diff = line
                break
        await resp.body_iterator.aclose()
        return diff

    diff = asyncio.run(run())
    diff_str = diff.decode() if isinstance(diff, bytes) else diff
    assert "table_id" in diff_str
