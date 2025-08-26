import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.auth import create_access_token
from api.app.routes_print_bridge import router as print_router


@pytest.fixture
def client():
    fake = fakeredis.aioredis.FakeRedis()
    calls = {"count": 0, "args": []}

    async def fake_publish(channel, msg):
        calls["count"] += 1
        calls["args"].append((channel, msg))

    fake.publish = fake_publish
    app = FastAPI()
    app.include_router(print_router)
    app.state.redis = fake
    return TestClient(app), calls


def test_notify_publishes_once(client):
    client, calls = client
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/outlet/demo/print/notify",
        json={"order_id": 1, "size": "80mm"},
        headers=headers,
    )
    assert resp.status_code == 204
    assert calls["count"] == 1
    assert calls["args"][0] == ("print:kot:demo", '{"order_id":1,"size":"80mm"}')
