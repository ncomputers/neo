import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.app import models_tenant
from api.app.models_tenant import Invoice
from api.app.repos_sqlalchemy import invoices_repo_sql


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_split_payments_settle_invoice(session):
    invoice = Invoice(
        order_group_id=1,
        number="INV1",
        bill_json={"subtotal": 100.0, "tax_breakup": {}, "total": 100.0},
        total=Decimal("100"),
    )
    session.add(invoice)
    await session.flush()

    await invoices_repo_sql.add_payment(session, invoice.id, "cash", 40, verified=True)
    await session.commit()
    refreshed = await session.get(Invoice, invoice.id)
    assert not refreshed.settled

    await invoices_repo_sql.add_payment(session, invoice.id, "card", 60, verified=True)
    await session.commit()
    refreshed = await session.get(Invoice, invoice.id)
    assert refreshed.settled
    assert refreshed.settled_at is not None
