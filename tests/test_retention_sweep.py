"""Verify retention sweep removes only expired rows."""

import importlib.util
import os
import pathlib
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from app.db.tenant import get_engine  # type: ignore
from api.app.models_tenant import Base, AuditTenant, NotificationOutbox  # type: ignore


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_sweep_prunes_old_rows(tmp_path, monkeypatch):
    tenant_id = "t1"
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )

    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("CREATE TABLE access_logs (id INTEGER PRIMARY KEY, created_at DATETIME)")
        )

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    old_ts = datetime.utcnow() - timedelta(days=40)
    new_ts = datetime.utcnow() - timedelta(days=5)

    async with Session() as session:
        session.add(AuditTenant(actor="a", action="old", at=old_ts))
        session.add(AuditTenant(actor="a", action="new", at=new_ts))
        session.add(
            NotificationOutbox(
                event="e",
                payload={},
                channel="c",
                target="t",
                status="delivered",
                created_at=old_ts,
                delivered_at=old_ts,
            )
        )
        session.add(
            NotificationOutbox(
                event="e",
                payload={},
                channel="c",
                target="t",
                status="delivered",
                created_at=new_ts,
                delivered_at=new_ts,
            )
        )
        await session.execute(
            text("INSERT INTO access_logs (created_at) VALUES (:o), (:n)"),
            {"o": old_ts, "n": new_ts},
        )
        await session.commit()

    spec = importlib.util.spec_from_file_location(
        "retention_sweep", ROOT / "scripts/retention_sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    await mod.sweep(tenant_id, 30)

    async with Session() as session:
        audit_count = (
            await session.execute(text("SELECT COUNT(*) FROM audit_tenant"))
        ).scalar()
        outbox_count = (
            await session.execute(text("SELECT COUNT(*) FROM notifications_outbox"))
        ).scalar()
        access_count = (
            await session.execute(text("SELECT COUNT(*) FROM access_logs"))
        ).scalar()

    assert audit_count == 1
    assert outbox_count == 1
    assert access_count == 1

    await engine.dispose()

