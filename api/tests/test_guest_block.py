import asyncio
import pathlib
import sys

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.hooks import order_rejection
from api.app.middlewares.guest_block import GuestBlockMiddleware
from api.app.security import ip_reputation
from api.app.security.blocklist import add_rejection, block_ip, clear_ip, is_blocked

app = FastAPI()
app.add_middleware(GuestBlockMiddleware)


@app.post("/g/echo")
async def _echo():  # pragma: no cover - simple test helper
    return {"ok": True}


def test_blocklist_helpers():
    redis = fakeredis.aioredis.FakeRedis()
    tenant = "demo"
    ip = "1.2.3.4"

    async def flow():
        assert await add_rejection(redis, tenant, ip) == 1
        assert await add_rejection(redis, tenant, ip) == 2
        assert not await is_blocked(redis, tenant, ip)
        await block_ip(redis, tenant, ip, ttl=10)
        assert await is_blocked(redis, tenant, ip)
        await clear_ip(redis, tenant, ip)
        assert not await is_blocked(redis, tenant, ip)
        assert await redis.exists(f"rej:{tenant}:ip:{ip}") == 0

    asyncio.run(flow())


def test_block_after_three_manual_rejections():
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis
    client = TestClient(app)

    async def _simulate():
        for _ in range(3):
            await order_rejection.on_rejected("demo", "testclient", redis)
        return await redis.ttl("blocklist:demo:ip:testclient")

    ttl = asyncio.run(_simulate())
    assert 0 < ttl <= 900

    resp = client.post("/g/echo", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 429
    data = resp.json()["error"]
    assert data["code"] == "ABUSE_COOLDOWN"
    assert data["hint"].startswith("Try again in ")


def test_user_agent_denylist():
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis
    client = TestClient(app)
    headers = {"X-Tenant-ID": "demo", "User-Agent": "curl/7.79"}
    resp = client.post("/g/echo", headers=headers)
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "UA_BLOCKED"


def test_ip_reputation_block():
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis
    client = TestClient(app)

    async def _mark():
        await ip_reputation.mark_bad(redis, "testclient")

    asyncio.run(_mark())

    resp = client.post("/g/echo", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "IP_BLOCKED"
