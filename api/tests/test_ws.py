import asyncio
import pathlib
import sys
from fakeredis import aioredis
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app
from api.app import models_tenant
from api.app.domain import OrderStatus
from api.app.repos_sqlalchemy import orders_repo_sql


client = TestClient(app)


def test_websocket_order_status_eta(monkeypatch):
    fake = aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)

    async def fake_load(session):
        return (10, 30.0)

    monkeypatch.setattr(orders_repo_sql.ema_repo_sql, "load", fake_load)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(models_tenant.Base.metadata.create_all)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            await session.execute(
                text(
                    "INSERT INTO tables (id, tenant_id, name, code, status, state, pos_x, pos_y) "
                    "VALUES (1, 't', 'T1', 'T1', 'available', 'AVAILABLE', 0, 0)"
                )
            )
            await session.execute(
                text(
                    "INSERT INTO orders (id, table_id, status) VALUES (1, 1, 'placed')"
                )
            )
            await session.commit()
            return 1, async_session

    order_id, Session = asyncio.run(setup())

    def do_update(status: str):
        async def inner():
            async with Session() as session:
                await orders_repo_sql.update_status(session, order_id, status)
        asyncio.run(inner())

    with client.websocket_connect("/tables/T1/ws") as ws:
        do_update(OrderStatus.IN_PROGRESS.value)
        first = ws.receive_json()
        assert first["status"] == "in_progress"
        assert first["order_id"] == str(order_id)
        eta1 = first["eta_secs"]

        do_update(OrderStatus.READY.value)
        second = ws.receive_json()
        assert second["status"] == "ready"
        assert second["eta_secs"] == 0
        assert second["eta_secs"] <= eta1

    asyncio.run(engine.dispose())
