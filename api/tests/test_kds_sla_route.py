import asyncio
import pathlib
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from api.app import routes_kds_sla
from api.app.models_tenant import Base, AlertRule, NotificationOutbox
from api.app.services import notifications


def test_kds_sla_breach_enqueue(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/tenant.db")

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_init())

    monkeypatch.setattr(notifications, "get_engine", lambda tid: engine)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _seed() -> None:
        async with SessionLocal() as session:
            session.add_all(
                [
                    AlertRule(event="sla_breach", channel="email", target="o@example.com"),
                    AlertRule(event="sla_breach", channel="whatsapp", target="123"),
                    AlertRule(event="sla_breach", channel="slack", target="#alerts"),
                ]
            )
            await session.commit()
    asyncio.run(_seed())

    app = FastAPI()
    app.include_router(routes_kds_sla.router)
    client = TestClient(app)

    payload = {
        "window": "15m",
        "breaches": [{"item": "Burger", "avg_prep": 12.0, "orders": 2, "table": 1}],
    }
    resp = client.post("/api/outlet/t1/kds/sla/breach", json=payload)
    assert resp.status_code == 200

    async def _count() -> int:
        async with SessionLocal() as session:
            rows = await session.execute(select(NotificationOutbox))
            return len(rows.scalars().all())

    assert asyncio.run(_count()) == 3
