import pytest
import pytest
import fakeredis.aioredis
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.auth import create_access_token


@pytest.fixture
def client():
    fake = fakeredis.aioredis.FakeRedis()
    calls = {"count": 0, "args": []}

    async def fake_publish(channel, msg):
        calls["count"] += 1
        calls["args"].append((channel, msg))

    fake.publish = fake_publish
    app.state.redis = fake
    return TestClient(app), calls


def test_notify_publishes_once(client):
    client, calls = client
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/outlet/demo/print/notify", json={"order_id": 1, "size": "80mm"}, headers=headers
    )
    assert resp.status_code == 204
    assert calls["count"] == 1
    assert calls["args"][0] == (
        "print:kot:demo", '{"order_id":1,"size":"80mm"}'
    )
