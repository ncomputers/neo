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
async def test_invoice_numbering_series_resets(session):
    series_a = invoice_counter.build_series("PFX", "never", date(2024, 1, 1))
    n1 = await invoice_counter.next_invoice_number(session, series_a)
    n2 = await invoice_counter.next_invoice_number(session, series_a)
    assert n1.endswith("/000001")
    assert n2.endswith("/000002")

    series_b = invoice_counter.build_series("NEW", "never", date(2024, 1, 1))
    n3 = await invoice_counter.next_invoice_number(session, series_b)
    assert n3.endswith("/000001")
