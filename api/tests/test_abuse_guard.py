import asyncio
import pathlib
import sys
import time

import fakeredis.aioredis
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.hooks import order_rejection
from api.app.routes_metrics import abuse_ip_cooldown
from api.app.security import blocklist
from api.app.security.abuse_guard import guard

app = FastAPI()


@app.post("/g/order")
async def _order(request: Request):  # pragma: no cover - helper
    await guard(request, "demo", app.state.redis)
    return {"ok": True}


def test_cooldown_then_release():
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis
    client = TestClient(app)

    async def _prepare():
        for _ in range(3):
            await order_rejection.on_rejected("demo", "testclient", redis)
        await redis.expire("blocklist:demo:ip:testclient", 1)

    asyncio.run(_prepare())

    resp = client.post("/g/order")
    assert resp.status_code == 429

    time.sleep(1.2)
    resp2 = client.post("/g/order")
    assert resp2.status_code == 200


def test_abuse_metric_and_hint():
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis
    client = TestClient(app)

    async def _prepare():
        await blocklist.block_ip(redis, "demo", "testclient", ttl=5)

    asyncio.run(_prepare())

    resp = client.post("/g/order")
    assert resp.status_code == 429
    data = resp.json()["detail"]["error"]
    assert data["code"] == "ABUSE_COOLDOWN"
    secs = int(data["hint"].split()[3][:-1])
    ttl = asyncio.run(blocklist.block_ttl(redis, "demo", "testclient"))
    assert abs(secs - ttl) <= 1
    metric = abuse_ip_cooldown._metrics[("testclient",)]._value.get()  # type: ignore[attr-defined]
    assert abs(metric - ttl) <= 1
