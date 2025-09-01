import asyncio
import datetime
import time
import pathlib
import sys

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import routes_admin_ops
from api.app.models_tenant import Base, Order, OrderStatus
from api.app.routes_metrics import webhook_attempts_total, webhook_failures_total


def test_admin_ops_summary(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(routes_admin_ops.router)
    app.state.redis = fakeredis.aioredis.FakeRedis()

    webhook_attempts_total.labels(destination="x").inc(5)
    webhook_failures_total.labels(destination="x").inc(1)

    now = int(time.time())
    asyncio.run(app.state.redis.set("cb:x:until", now + 30))

    async def fake_preflight():
        return {"status": "ok"}

    monkeypatch.setattr(routes_admin_ops, "preflight", fake_preflight)

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/t.db")

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init_db())

    async def seed():
        async with AsyncSession(engine) as session:
            now_dt = datetime.datetime.utcnow()
            order = Order(
                table_id=1,
                status=OrderStatus.READY,
                accepted_at=now_dt,
                ready_at=now_dt + datetime.timedelta(seconds=30),
            )
            session.add(order)
            await session.commit()
    asyncio.run(seed())

    monkeypatch.setattr(routes_admin_ops, "get_engine", lambda tenant: engine)

    client = TestClient(app)
    resp = client.get("/api/admin/ops/summary", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["uptime"] == "ok"
    assert round(data["webhook_success_rate"], 1) == 0.8
    # Account for small delays between setting and reading the breaker TTL
    assert data["breaker_open_time"] >= 29
    assert data["median_kot_prep_time"] == 30.0
