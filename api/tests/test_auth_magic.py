import pathlib
import sys
from datetime import timedelta

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import asyncio  # noqa: E402
import hmac  # noqa: E402
import os  # noqa: E402
import uuid  # noqa: E402
from hashlib import sha256  # noqa: E402

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


def test_magic_login_throttling_and_captcha():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    os.environ["CAPTCHA_SECRET"] = "test-secret"
    local_client = TestClient(app)
    email = "ip@example.com"
    ip = "testclient"
    token_hmac = hmac.new(
        os.environ["CAPTCHA_SECRET"].encode(), f"{ip}:{email}".encode(), sha256
    ).hexdigest()

    for _ in range(2):
        assert (
            local_client.post("/auth/magic/start", json={"email": email}).status_code
            == 200
        )

    resp_limit = local_client.post("/auth/magic/start", json={"email": email})
    assert resp_limit.status_code == 429
    body = resp_limit.json()
    assert body["code"] == "RATE_LIMIT"
    assert "retry in" in body["hint"]

    for _ in range(3):
        assert (
            local_client.post(
                "/auth/magic/start",
                json={"email": email},
                headers={"X-Captcha-Token": token_hmac},
            ).status_code
            == 200
        )

    asyncio.run(app.state.redis.delete(f"ratelimit:{ip}:magic-start"))

    resp_limit2 = local_client.post("/auth/magic/start", json={"email": email})
    assert resp_limit2.status_code == 429
    body2 = resp_limit2.json()
    assert body2["code"] == "RATE_LIMIT"
    assert "retry in" in body2["hint"]

    assert (
        local_client.post(
            "/auth/magic/start",
            json={"email": email},
            headers={"X-Captcha-Token": token_hmac},
        ).status_code
        == 200
    )

    jti = str(uuid.uuid4())
    token = create_access_token(
        {"sub": "owner@example.com", "jti": jti, "scope": "magic"},
        expires_delta=timedelta(seconds=-1),
    )
    asyncio.run(app.state.redis.set(f"magic:{jti}", "owner@example.com"))
    resp = local_client.get(f"/auth/magic/consume?token={token}")
    assert resp.status_code == 400
