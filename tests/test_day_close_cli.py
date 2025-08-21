import importlib.util
import os
import pathlib
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from app.db.tenant import get_engine  # type: ignore
from app import models_tenant  # type: ignore
from app.models_tenant import Invoice, Payment  # type: ignore
from app.models_master import SyncOutbox  # type: ignore

os.environ.setdefault("POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db")
os.environ.setdefault("DEFAULT_TZ", "UTC")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_setup():
    tenant_id = "test_" + uuid4().hex[:8]
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
        await conn.run_sync(SyncOutbox.__table__.create)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
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
        yield tenant_id, engine, Session
    finally:
        if engine.url.get_backend_name().startswith("sqlite"):
            await engine.dispose()
            db_path = engine.url.database
            if db_path and os.path.exists(db_path):
                os.remove(db_path)
        else:  # pragma: no cover - non-sqlite cleanup path
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
            await engine.dispose()


@pytest.mark.anyio
async def test_day_close_enqueues_notification(tenant_setup):
    tenant_id, engine, Session = tenant_setup
    spec = importlib.util.spec_from_file_location("day_close", "scripts/day_close.py")
    day_close = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(day_close)
    await day_close.main(tenant_id, "2024-01-01")
    async with Session() as session:
        result = await session.execute(select(SyncOutbox))
        event = result.scalar_one()
        assert event.event_type == "dayclose"
        assert event.payload["total"] == 105.0
        assert event.payload["payments"]["cash"] == 105.0
