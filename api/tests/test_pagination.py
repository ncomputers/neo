"""Pagination tests for admin list endpoints."""

import asyncio
import importlib
import pathlib
import sys
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import audit  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.models_tenant import (  # noqa: E402
    Base,
    NotificationDLQ,
    NotificationOutbox,
)


def _admin_headers():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


def _setup_outbox(tmp_path, monkeypatch):
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


def _setup_audit(tmp_path):
    from api.app import routes_admin_audit

    audit.engine = create_engine(f"sqlite:///{tmp_path/'audit.db'}")
    audit.SessionLocal = sessionmaker(bind=audit.engine)
    audit.Base.metadata.create_all(bind=audit.engine)
    importlib.reload(routes_admin_audit)
    app = FastAPI()
    app.include_router(routes_admin_audit.router)
    client = TestClient(app)
    return client


def test_outbox_pagination_and_limit(tmp_path, monkeypatch):
    client, tenant_id, SessionLocal = _setup_outbox(tmp_path, monkeypatch)

    async def seed() -> None:
        async with SessionLocal() as session:
            for i in range(120):
                session.add(
                    NotificationOutbox(
                        event="e",
                        payload={},
                        channel="sms",
                        target=str(i),
                        status="queued",
                        attempts=0,
                        created_at=datetime.now(timezone.utc),
                    )
                )
            await session.commit()

    asyncio.run(seed())
    resp = client.get(
        f"/api/outlet/{tenant_id}/outbox",
        params={"limit": 200},
        headers=_admin_headers(),
    )
    data = resp.json()["data"]
    assert len(data) == 100
    cursor = data[-1]["id"]
    resp = client.get(
        f"/api/outlet/{tenant_id}/outbox",
        params={"cursor": cursor},
        headers=_admin_headers(),
    )
    assert len(resp.json()["data"]) == 20


def test_dlq_pagination_and_limit(tmp_path, monkeypatch):
    client, tenant_id, SessionLocal = _setup_outbox(tmp_path, monkeypatch)

    async def seed() -> None:
        async with SessionLocal() as session:
            for i in range(120):
                session.add(
                    NotificationDLQ(
                        original_id=i,
                        event="e",
                        channel="sms",
                        target=str(i),
                        payload={},
                        error="boom",
                        failed_at=datetime.now(timezone.utc),
                    )
                )
            await session.commit()

    asyncio.run(seed())
    resp = client.get(
        f"/api/outlet/{tenant_id}/dlq",
        params={"limit": 500},
        headers=_admin_headers(),
    )
    data = resp.json()["data"]
    assert len(data) == 100
    cursor = data[-1]["id"]
    resp = client.get(
        f"/api/outlet/{tenant_id}/dlq",
        params={"cursor": cursor},
        headers=_admin_headers(),
    )
    assert len(resp.json()["data"]) == 20


def test_audit_log_pagination_and_limit(tmp_path):
    client = _setup_audit(tmp_path)
    with audit.SessionLocal() as session:
        for i in range(120):
            session.add(audit.Audit(actor="a", action="x", entity=str(i)))
        session.commit()
    resp = client.get(
        "/api/admin/audit/logs", params={"limit": 1000}, headers=_admin_headers()
    )
    data = resp.json()["data"]
    assert len(data) == 100
    cursor = data[-1]["id"]
    resp = client.get(
        "/api/admin/audit/logs", params={"cursor": cursor}, headers=_admin_headers()
    )
    assert len(resp.json()["data"]) == 20
