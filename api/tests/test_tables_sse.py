import asyncio
import json
import pathlib
import sys

import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import routes_tables_sse


def test_tables_sse_reconnect_snapshot_first(monkeypatch):
    """On reconnect, snapshot precedes incremental updates."""
    fake = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)

    async def seed_initial():
        resp = await routes_tables_sse.stream_table_map("demo", None)
        await resp.body_iterator.__anext__()  # snapshot id 1
        await fake.publish(
            "rt:table_map:demo",
            json.dumps({"table_id": "t1", "code": "T1", "state": "LOCKED", "x": 1, "y": 2, "ts": 0}),
        )
        await asyncio.sleep(0)
        await resp.body_iterator.__anext__()  # diff id 2
        await resp.body_iterator.aclose()

    asyncio.run(seed_initial())

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
