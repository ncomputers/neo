from datetime import datetime

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_print_test import router


def test_admin_print_test_previews_and_publishes():
    fake = fakeredis.aioredis.FakeRedis()
    calls = {"count": 0, "channel": None, "msg": None}

    async def fake_publish(channel, msg):
        calls["count"] += 1
        calls["channel"] = channel
        calls["msg"] = msg

    fake.publish = fake_publish
    app = FastAPI()
    app.include_router(router)
    app.state.redis = fake
    client = TestClient(app)

    resp = client.post("/admin/print/test", json={"printer": "80mm"})
    assert resp.status_code == 200
    body = resp.text
    assert "outlet" in body
    assert "title" in body
    assert "timestamp" in body
    ts_line = next(line for line in body.splitlines() if line.startswith("timestamp:"))
    datetime.fromisoformat(ts_line.split("timestamp: ", 1)[1])
    assert calls["count"] == 1
    assert calls["channel"] == "print:test:80mm"
