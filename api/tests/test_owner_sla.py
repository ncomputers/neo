import asyncio
import datetime
import pathlib
import sys

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import routes_owner_sla
from api.app.models_tenant import Base, Order, OrderStatus
from api.app.routes_metrics import (
    webhook_attempts_total,
    webhook_failures_total,
    db_replica_healthy,
    kot_delay_alerts_total,
)


def test_owner_sla(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(routes_owner_sla.router)
    app.state.redis = fakeredis.aioredis.FakeRedis()

    webhook_attempts_total.clear()
    webhook_failures_total.clear()
    kot_delay_alerts_total._value.set(0)
    db_replica_healthy.set(1)

    # Counters hold cumulative totals. Seed previous 7-day snapshot and current
    # increments separately for trend verification.
    app.state.owner_sla_history = {
        "webhook_attempts_14d": 0,
        "webhook_failures_14d": 0,
        "webhook_attempts_7d": 4,
        "webhook_failures_7d": 1,
        "kot_delay_alerts_14d": 0,
        "kot_delay_alerts_7d": 1,
        "uptime_prev": 90.0,
    }

    webhook_attempts_total.labels(destination="x").inc(7)  # 4 prev + 3 current
    webhook_failures_total.labels(destination="x").inc(2)  # 1 prev + 1 current
    kot_delay_alerts_total.inc(3)  # 1 prev + 2 current

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/t.db")

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init_db())

    async def seed():
        async with AsyncSession(engine) as session:
            now = datetime.datetime.utcnow()
            order_curr = Order(
                table_id=1,
                status=OrderStatus.READY,
                accepted_at=now,
                ready_at=now + datetime.timedelta(seconds=20),
            )
            order_prev = Order(
                table_id=1,
                status=OrderStatus.READY,
                accepted_at=now - datetime.timedelta(days=8),
                ready_at=now - datetime.timedelta(days=8) + datetime.timedelta(seconds=40),
            )
            session.add_all([order_curr, order_prev])
            await session.commit()
    asyncio.run(seed())

    monkeypatch.setattr(routes_owner_sla, "get_engine", lambda tenant: engine)

    client = TestClient(app)
    resp = client.get("/api/owner/sla", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["uptime_7d"] == 100.0
    assert data["uptime_trend"] == 10.0
    assert round(data["webhook_success"], 2) == 0.67
    assert round(data["webhook_success_trend"], 2) == -0.08
    assert data["median_prep"] == 20.0
    assert data["median_prep_trend"] == -20.0
    assert data["kot_delay_alerts"] == 2
    assert data["kot_delay_alerts_trend"] == 1
