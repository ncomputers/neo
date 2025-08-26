from __future__ import annotations

import asyncio
import datetime

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_metrics import router as metrics_router
from api.app.routes_print_bridge import router as print_router


def test_printer_status_and_metrics():
    app = FastAPI()
    app.include_router(print_router)
    app.include_router(metrics_router)
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis

    tenant = "demo"
    stale_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=5
    )

    async def seed() -> None:
        await redis.set(f"print:hb:{tenant}", stale_time.isoformat())
        await redis.rpush(f"print:retry:{tenant}", "job1")

    asyncio.run(seed())

    client = TestClient(app)
    resp = client.get(f"/api/outlet/{tenant}/print/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale"] is True
    assert data["queue"] == 1

    body = client.get("/metrics").text
    assert "printer_retry_queue 1.0" in body
