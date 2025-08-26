import asyncio
import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app  # noqa: E402
from api.app import routes_exports  # noqa: E402


def test_exports_ratelimit(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()

    async def _allow(redis, ip, key, rate_per_min=60, burst=1):
        return False

    monkeypatch.setattr(routes_exports.ratelimit, "allow", _allow)

    # simulate existing TTL for retry hint
    asyncio.run(app.state.redis.setex("ratelimit:testclient:exports", 15, 1))

    client = TestClient(app)
    resp = client.get(
        "/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-01"
    )
    assert resp.status_code == 429
    body = resp.json()
    assert body["code"] == "RATE_LIMIT"
    assert "retry in" in body["hint"]
