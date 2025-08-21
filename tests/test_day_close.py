from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.app.db.tenant import get_engine as get_tenant_engine
from api.app.models_tenant import Base as TenantBase, Invoice, Payment
from api.app.models_master import Base as MasterBase, SyncOutbox


def _setup_tenant(tenant_id: str) -> None:
    async def _init() -> None:
        engine = get_tenant_engine(tenant_id)
        async with engine.begin() as conn:
            await conn.run_sync(TenantBase.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with Session() as session:
            invoice = Invoice(
                order_group_id=1,
                number="INV1",
                bill_json={"subtotal": 100.0, "tax_breakup": {5: 5.0}, "total": 105.0},
                total=105.0,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(invoice)
            await session.flush()
            payment = Payment(
                invoice_id=invoice.id,
                mode="cash",
                amount=105.0,
                verified=True,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(payment)
            await session.commit()
        await engine.dispose()

    asyncio.run(_init())


def _setup_master() -> None:
    async def _init() -> None:
        engine = create_async_engine(os.environ["POSTGRES_MASTER_URL"])
        async with engine.begin() as conn:
            await conn.run_sync(MasterBase.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())


def test_day_close_cli(tmp_path, monkeypatch):
    tenant_id = "demo"
    monkeypatch.setenv(
        "POSTGRES_TENANT_DSN_TEMPLATE",
        f"sqlite+aiosqlite:///{tmp_path}/tenant_{{tenant_id}}.db",
    )
    monkeypatch.setenv(
        "POSTGRES_MASTER_URL", f"sqlite+aiosqlite:///{tmp_path/'master.db'}"
    )

    _setup_tenant(tenant_id)
    _setup_master()

    subprocess.check_call(
        [sys.executable, "scripts/day_close.py", "--tenant", tenant_id, "--date", "2024-01-01"]
    )

    async def _fetch() -> list[SyncOutbox]:
        engine = create_async_engine(os.environ["POSTGRES_MASTER_URL"])
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with Session() as session:
            events = (await session.execute(select(SyncOutbox))).scalars().all()
        await engine.dispose()
        return events

    events = asyncio.run(_fetch())
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "dayclose"
    assert event.payload["totals"]["total"] == 105.0
    assert event.payload["totals"]["payments"]["cash"] == 105.0
