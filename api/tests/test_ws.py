import asyncio
import json
import pathlib
import sys

from fakeredis import aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app


client = TestClient(app)


def test_websocket_order_status_eta(monkeypatch):
    fake = aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)

    with client.websocket_connect("/tables/T1/ws") as ws:
        async def publish(status, eta):
            payload = json.dumps({"status": status, "eta": eta})
            await fake.publish("rt:update:T1", payload)

        asyncio.run(publish("in_progress", 10))
        first = ws.receive_json()
        assert first["status"] == "in_progress"
        assert first["eta"] == 10

        asyncio.run(publish("ready", 0))
        second = ws.receive_json()
        assert second["status"] == "ready"
        assert second["eta"] == 0
        assert second["eta"] < first["eta"]
