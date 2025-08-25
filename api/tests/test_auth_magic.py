import pathlib
import sys
from datetime import timedelta

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import asyncio  # noqa: E402
import uuid  # noqa: E402

import fakeredis.aioredis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.app.auth import create_access_token  # noqa: E402
from api.app.main import app  # noqa: E402

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def test_magic_login_happy_path():
    resp = client.post("/auth/magic/start", json={"email": "owner@example.com"})
    assert resp.status_code == 200
    token = resp.json()["data"]["token"]
    resp2 = client.get(f"/auth/magic/consume?token={token}")
    assert resp2.status_code == 200
    assert "access_token" in resp2.json()["data"]
    # token is single-use
    resp3 = client.get(f"/auth/magic/consume?token={token}")
    assert resp3.status_code == 400


def test_magic_login_throttling_and_expiry():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    local_client = TestClient(app)
    for _ in range(3):
        assert (
            local_client.post(
                "/auth/magic/start", json={"email": "ip@example.com"}
            ).status_code
            == 200
        )
    assert (
        local_client.post(
            "/auth/magic/start", json={"email": "ip@example.com"}
        ).status_code
        == 429
    )

    jti = str(uuid.uuid4())
    token = create_access_token(
        {"sub": "owner@example.com", "jti": jti, "scope": "magic"},
        expires_delta=timedelta(seconds=-1),
    )
    asyncio.run(app.state.redis.set(f"magic:{jti}", "owner@example.com"))
    resp = local_client.get(f"/auth/magic/consume?token={token}")
    assert resp.status_code == 400
