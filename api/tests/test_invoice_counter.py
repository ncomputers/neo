import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from datetime import date

import pytest

from api.app import models_tenant
from api.app.utils import invoice_counter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as sess:
        yield sess


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_invoice_numbering_never_runs(session):
    jan = invoice_counter.build_series("NEV", "never", date(2024, 1, 1))
    feb = invoice_counter.build_series("NEV", "never", date(2024, 2, 1))
    n1 = await invoice_counter.next_invoice_number(session, jan)
    n2 = await invoice_counter.next_invoice_number(session, feb)
    assert n1 == "INV-NEV-0001"
    assert n2 == "INV-NEV-0002"


@pytest.mark.anyio
async def test_invoice_numbering_monthly_reset(session):
    jan = invoice_counter.build_series("MON", "monthly", date(2024, 1, 1))
    feb = invoice_counter.build_series("MON", "monthly", date(2024, 2, 1))

    jan_1 = await invoice_counter.next_invoice_number(session, jan)
    jan_2 = await invoice_counter.next_invoice_number(session, jan)
    feb_1 = await invoice_counter.next_invoice_number(session, feb)

    assert jan_1 == "INV-MON-202401-0001"
    assert jan_2 == "INV-MON-202401-0002"
    assert feb_1 == "INV-MON-202402-0001"
