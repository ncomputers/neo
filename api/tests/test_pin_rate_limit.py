import asyncio
import time

import fakeredis.aioredis
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.security import pin_lockout


def test_pin_rate_limit_does_not_block_ip():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    redis = app.state.redis
    ip = "testclient"
    key = f"ratelimit:/login/pin:-:{ip}"
    now = int(time.time())
    for i in range(10):
        asyncio.run(redis.zadd(key, {str(i): now}))
    asyncio.run(redis.expire(key, 300))

    client = TestClient(app)
    payload = {"username": "cashier1", "pin": "1234"}
    res1 = client.post("/login/pin", json=payload)
    assert res1.status_code == 429
    assert "Retry-After" in res1.headers

    res2 = client.post("/login/pin", json=payload)
    assert res2.status_code == 429

    locked = asyncio.run(pin_lockout.is_locked(redis, "demo", "cashier1", ip))
    assert locked is False
    fail_key = f"pin:fail:demo:cashier1:{ip}"
    assert asyncio.run(redis.get(fail_key)) is None

