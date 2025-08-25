"""Verify tenant retention policy enforcement."""

import importlib
import importlib.util
import os
import pathlib
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from app.db.tenant import get_engine as get_tenant_engine  # type: ignore
from api.app.models_master import Base as MasterBase, Tenant  # type: ignore
from api.app.models_tenant import Base as TenantBase, AuditTenant, NotificationOutbox  # type: ignore


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_retention_enforce(tmp_path, monkeypatch):
    tenant_name = "demo"
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    monkeypatch.setenv(
        "POSTGRES_MASTER_URL", f"sqlite+aiosqlite:///{tmp_path/'master.db'}",
    )

    import app.db.master as master_db
    import app.db.tenant as tenant_db
    importlib.reload(master_db)
    importlib.reload(tenant_db)

    # Set up master with retention policy
    m_engine = create_async_engine(os.environ["POSTGRES_MASTER_URL"])
    async with m_engine.begin() as conn:
        await conn.run_sync(MasterBase.metadata.create_all)
    MSession = async_sessionmaker(m_engine, expire_on_commit=False, class_=AsyncSession)
    async with MSession() as session:
        tenant_row = Tenant(
            name=tenant_name,
            retention_days_customers=30,
            retention_days_outbox=30,
        )
        session.add(tenant_row)
        await session.commit()
        tenant_id = str(tenant_row.id)
    await m_engine.dispose()

    # Set up tenant database with sample data
    t_engine = get_tenant_engine(tenant_id)
    async with t_engine.begin() as conn:
        await conn.run_sync(AuditTenant.__table__.create)
        await conn.run_sync(NotificationOutbox.__table__.create)
        await conn.execute(
            text(
                "CREATE TABLE access_logs (id INTEGER PRIMARY KEY, created_at DATETIME)"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, created_at DATETIME)"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE invoices (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, created_at DATETIME)"
            )
        )

    Session = async_sessionmaker(t_engine, expire_on_commit=False, class_=AsyncSession)

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
        await session.execute(
            text(
                "INSERT INTO customers (name, phone, email, created_at) "
                "VALUES ('old', '1', 'o@example.com', :o), "
                "('new', '2', 'n@example.com', :n)"
            ),
            {"o": old_ts, "n": new_ts},
        )
        await session.execute(
            text(
                "INSERT INTO invoices (name, phone, email, created_at) "
                "VALUES ('old', '1', 'o@example.com', :o), "
                "('new', '2', 'n@example.com', :n)"
            ),
            {"o": old_ts, "n": new_ts},
        )
        await session.commit()

    spec = importlib.util.spec_from_file_location(
        "retention_enforce", ROOT / "scripts/retention_enforce.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    await mod.enforce(tenant_name)

    async with Session() as session:
        audit_count = (await session.execute(text("SELECT COUNT(*) FROM audit_tenant"))).scalar()
        outbox_count = (await session.execute(text("SELECT COUNT(*) FROM notifications_outbox"))).scalar()
        access_count = (await session.execute(text("SELECT COUNT(*) FROM access_logs"))).scalar()
        cust_rows = (
            await session.execute(
                text("SELECT name, phone, email FROM customers ORDER BY id")
            )
        ).all()
        inv_rows = (
            await session.execute(
                text("SELECT name, phone, email FROM invoices ORDER BY id")
            )
        ).all()

    assert audit_count == 2
    assert outbox_count == 1
    assert access_count == 1
    assert cust_rows[0] == (None, None, None)
    assert cust_rows[1] == ("new", "2", "n@example.com")
    assert inv_rows[0] == (None, None, None)
    assert inv_rows[1] == ("new", "2", "n@example.com")

    await t_engine.dispose()
