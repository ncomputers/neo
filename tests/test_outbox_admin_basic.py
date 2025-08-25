import asyncio
import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app.models_tenant import (  # noqa: E402
    Base,
    NotificationDLQ,
    NotificationOutbox,
)


def _setup(tmp_path, monkeypatch):
    import api.app.auth as auth

    monkeypatch.setattr(auth, "role_required", lambda *roles: lambda: object())
    from api.app import routes_outbox_admin

    importlib.reload(routes_outbox_admin)

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'tenant.db'}")

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    tenant_id = "t1"
    monkeypatch.setattr(routes_outbox_admin, "get_engine", lambda tid: engine)

    app = FastAPI()
    app.include_router(routes_outbox_admin.router)
    client = TestClient(app)

    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    return client, tenant_id, SessionLocal


def test_outbox_list_and_retry(tmp_path, monkeypatch):
    client, tenant_id, SessionLocal = _setup(tmp_path, monkeypatch)

    async def seed() -> int:
        async with SessionLocal() as session:
            event = NotificationOutbox(
                event="foo",
                payload={},
                channel="sms",
                target="123",
                status="delivered",
                attempts=1,
            )
            session.add(event)
            await session.commit()
            return event.id

    event_id = asyncio.run(seed())

    resp = client.get(f"/api/outlet/{tenant_id}/outbox", params={"status": "delivered"})
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == event_id

    resp = client.post(f"/api/outlet/{tenant_id}/outbox/{event_id}/retry")
    assert resp.status_code == 200

    async def check() -> None:
        async with SessionLocal() as session:
            obj = await session.get(NotificationOutbox, event_id)
            assert obj.status == "queued"
            assert obj.attempts == 0

    asyncio.run(check())


def test_dlq_list_and_requeue(tmp_path, monkeypatch):
    client, tenant_id, SessionLocal = _setup(tmp_path, monkeypatch)

    async def seed() -> int:
        async with SessionLocal() as session:
            entry = NotificationDLQ(
                original_id=1,
                event="foo",
                channel="sms",
                target="123",
                payload={},
                error="boom",
            )
            session.add(entry)
            await session.commit()
            return entry.id

    dlq_id = asyncio.run(seed())

    resp = client.get(f"/api/outlet/{tenant_id}/dlq")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == dlq_id

    resp = client.post(f"/api/outlet/{tenant_id}/dlq/{dlq_id}/requeue")
    assert resp.status_code == 200

    async def check() -> None:
        async with SessionLocal() as session:
            outbox_rows = (
                (await session.execute(select(NotificationOutbox))).scalars().all()
            )
            dlq = await session.get(NotificationDLQ, dlq_id)
            assert len(outbox_rows) == 1
            assert dlq is None

    asyncio.run(check())
