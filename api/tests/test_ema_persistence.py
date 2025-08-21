import os
import pathlib
import sys
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///tenant_{tenant_id}.db"
)

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import db as app_db  # noqa: E402
from api.app import domain as app_domain  # noqa: E402
from api.app import models_tenant as app_models_tenant  # noqa: E402
from api.app import repos_sqlalchemy as app_repos_sqlalchemy  # noqa: E402
from api.app import utils as app_utils  # noqa: E402

import sys as _sys  # noqa: E402

_sys.modules.setdefault("db", app_db)
_sys.modules.setdefault("domain", app_domain)
_sys.modules.setdefault("models_tenant", app_models_tenant)
_sys.modules.setdefault("repos_sqlalchemy", app_repos_sqlalchemy)
_sys.modules.setdefault("utils", app_utils)

from api.app.domain import OrderStatus  # noqa: E402
from api.app.models_tenant import Base, EMAStat, Order, OrderStatus as ModelOrderStatus  # noqa: E402
from api.app import routes_kds  # noqa: E402
from api.app.services import ema as ema_service  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402


def test_ema_updates_persist(monkeypatch):
    asyncio.run(_run_test(monkeypatch))


async def _run_test(monkeypatch):
    tenant_id = "test_" + uuid4().hex[:8]
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as tenant_session:
        @asynccontextmanager
        async def _fake_session(_tenant_id: str):
            yield tenant_session

        monkeypatch.setattr(routes_kds, "_session", _fake_session)

        now = datetime.now(timezone.utc)
        order1 = Order(
            table_id=1,
            status=ModelOrderStatus.READY,
            accepted_at=now - timedelta(seconds=10),
        )
        tenant_session.add(order1)
        await tenant_session.commit()
        sample1 = (datetime.now(timezone.utc) - order1.accepted_at).total_seconds()
        await routes_kds._transition_order("t", order1.id, OrderStatus.SERVED)
        ema1 = float(await tenant_session.scalar(select(EMAStat.ema_seconds)))
        assert ema1 == pytest.approx(sample1, rel=0.1)

        order2 = Order(
            table_id=1,
            status=ModelOrderStatus.READY,
            accepted_at=now - timedelta(seconds=20),
        )
        tenant_session.add(order2)
        await tenant_session.commit()
        sample2 = (datetime.now(timezone.utc) - order2.accepted_at).total_seconds()
        await routes_kds._transition_order("t", order2.id, OrderStatus.SERVED)
        ema2 = float(await tenant_session.scalar(select(EMAStat.ema_seconds)))

        expected = ema_service.update_ema(ema1, sample2, 10)
        assert ema2 == pytest.approx(expected, rel=0.1)
    await engine.dispose()
