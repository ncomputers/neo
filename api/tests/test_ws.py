import asyncio
import json

from fakeredis import aioredis
from fastapi.testclient import TestClient

from api.app.main import app


client = TestClient(app)


def test_websocket_broadcasts_eta(monkeypatch):
    fake = aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)
    monkeypatch.setattr("api.app.main.prep_trackers", {})

    with client.websocket_connect("/tables/T1/ws") as ws:
        async def publish(prep_time):
            payload = json.dumps({"prep_time": prep_time, "status": "preparing"})
            await fake.publish("rt:update:T1", payload)

        asyncio.run(publish(10))
        first = ws.receive_json()
        assert first["eta"] == 10

        asyncio.run(publish(20))
        second = ws.receive_json()
        assert second["eta"] > 10
