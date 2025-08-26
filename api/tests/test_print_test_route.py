import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_print_test import router


def test_admin_print_test_previews_and_publishes():
    fake = fakeredis.aioredis.FakeRedis()
    calls = {"count": 0}

    async def fake_publish(channel, msg):
        calls["count"] += 1

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
    assert calls["count"] == 1
