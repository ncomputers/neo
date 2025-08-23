"""Tests covering admin outbox and dead-letter queue routes."""

import asyncio
import importlib
import pathlib
import sys
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.auth import create_access_token
from api.app.models_tenant import Base, NotificationOutbox, NotificationDLQ

def _setup(tmp_path, monkeypatch):
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
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return client, tenant_id, SessionLocal

def _admin_headers():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}

def _cashier_headers():
    token = create_access_token({"sub": "cashier1", "role": "cashier"})
    return {"Authorization": f"Bearer {token}"}

def test_outbox_pending_and_retry(tmp_path, monkeypatch):
    client, tenant_id, SessionLocal = _setup(tmp_path, monkeypatch)
    async def seed() -> int:
        async with SessionLocal() as session:
            event = NotificationOutbox(
                event="foo",
                payload={},
                channel="sms",
                target="123",
                status="queued",
                attempts=1,
                next_attempt_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
            session.add(event)
            await session.commit()
            return event.id
    event_id = asyncio.run(seed())
    resp = client.get(f"/api/outlet/{tenant_id}/outbox")
    assert resp.status_code == 401
    resp = client.get(f"/api/outlet/{tenant_id}/outbox", headers=_cashier_headers())
    assert resp.status_code == 403
    resp = client.get(
        f"/api/outlet/{tenant_id}/outbox",
        params={"status": "pending"},
        headers=_admin_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    row = data[0]
    assert row["id"] == event_id
    assert row["attempts"] == 1
    assert row["next_attempt_at"] is not None
    resp = client.post(
        f"/api/outlet/{tenant_id}/outbox/{event_id}/retry",
        headers=_admin_headers(),
    )
    assert resp.status_code == 200
    resp = client.get(
        f"/api/outlet/{tenant_id}/outbox",
        params={"status": "pending"},
        headers=_admin_headers(),
    )
    row = resp.json()["data"][0]
    assert row["attempts"] == 0
    assert row["next_attempt_at"] is None
    async def check() -> None:
        async with SessionLocal() as session:
            obj = await session.get(NotificationOutbox, event_id)
            assert obj.status == "queued"
            assert obj.attempts == 0
            assert obj.next_attempt_at is None
    asyncio.run(check())

def test_dlq_admin_flow(tmp_path, monkeypatch):
    client, tenant_id, SessionLocal = _setup(tmp_path, monkeypatch)
    async def seed() -> tuple[int, int]:
        async with SessionLocal() as session:
            d1 = NotificationDLQ(
                original_id=1,
                event="foo",
                channel="sms",
                target="123",
                payload={},
                error="boom",
            )
            d2 = NotificationDLQ(
                original_id=2,
                event="bar",
                channel="sms",
                target="456",
                payload={},
                error="oops",
            )
            session.add_all([d1, d2])
            await session.commit()
            return d1.id, d2.id
    dlq1, dlq2 = asyncio.run(seed())
    resp = client.get(f"/api/outlet/{tenant_id}/dlq", headers=_cashier_headers())
    assert resp.status_code == 403
    resp = client.get(f"/api/outlet/{tenant_id}/dlq", headers=_admin_headers())
    data = resp.json()["data"]
    assert {row["id"] for row in data} == {dlq1, dlq2}
    resp = client.post(
        f"/api/outlet/{tenant_id}/dlq/{dlq1}/requeue",
        headers=_admin_headers(),
    )
    assert resp.status_code == 200
    async def check_requeue() -> None:
        async with SessionLocal() as session:
            outbox_rows = (await session.execute(select(NotificationOutbox))).scalars().all()
            dlq_obj = await session.get(NotificationDLQ, dlq1)
            assert len(outbox_rows) == 1
            assert outbox_rows[0].status == "queued"
            assert dlq_obj is None
    asyncio.run(check_requeue())
    resp = client.delete(
        f"/api/outlet/{tenant_id}/dlq/{dlq2}",
        headers=_admin_headers(),
    )
    assert resp.status_code == 200
    async def check_delete() -> None:
        async with SessionLocal() as session:
            assert await session.get(NotificationDLQ, dlq2) is None
    asyncio.run(check_delete())
    resp = client.get(f"/api/outlet/{tenant_id}/dlq", headers=_admin_headers())
    assert resp.json()["data"] == []
    resp = client.get(
        f"/api/outlet/{tenant_id}/outbox",
        params={"status": "pending"},
        headers=_admin_headers(),
    )
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["attempts"] == 0
    assert data[0]["next_attempt_at"] is None
