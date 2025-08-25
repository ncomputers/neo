import importlib.util
import pathlib
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from app.db.tenant import get_engine  # type: ignore  # noqa: E402
from api.app.models_master import Base as MasterBase, Tenant  # type: ignore  # noqa: E402
from api.app.models_tenant import (  # type: ignore  # noqa: E402
    AlertRule,
    AuditTenant,
    OrderItem,
    NotificationOutbox,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_sla_breach_enqueues(tmp_path, monkeypatch):
    tenant_id = "t1"
    master_url = f"sqlite+aiosqlite:///{tmp_path}/master.db"
    tenant_template = f"sqlite+aiosqlite:///{tmp_path}/{{tenant_id}}.db"
    monkeypatch.setenv("POSTGRES_URL", master_url)
    monkeypatch.setenv("POSTGRES_TENANT_DSN_TEMPLATE", tenant_template)

    master_engine = create_async_engine(master_url)
    async with master_engine.begin() as conn:
        await conn.run_sync(MasterBase.metadata.create_all)
    MasterSession = async_sessionmaker(
        master_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with MasterSession() as session:
        session.add(Tenant(name=tenant_id, kds_sla_secs=1))
        await session.commit()

    tenant_engine = get_engine(tenant_id)
    async with tenant_engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE orders (id INTEGER PRIMARY KEY, table_id INTEGER, "
                "status TEXT)"
            )
        )
        await conn.execute(text("CREATE TABLE menu_items (id INTEGER PRIMARY KEY)"))
        await conn.run_sync(AlertRule.__table__.create)
        await conn.run_sync(NotificationOutbox.__table__.create)
        await conn.run_sync(AuditTenant.__table__.create)
        await conn.run_sync(OrderItem.__table__.create)
    TenantSession = async_sessionmaker(
        tenant_engine, expire_on_commit=False, class_=AsyncSession
    )

    now = datetime.utcnow()
    async with TenantSession() as session:
        await session.execute(
            text("INSERT INTO orders (id, table_id, status) VALUES (1,1,'new')")
        )
        await session.execute(
            text("INSERT INTO orders (id, table_id, status) VALUES (2,2,'new')")
        )
        await session.execute(
            text("INSERT INTO orders (id, table_id, status) VALUES (3,2,'new')")
        )
        await session.execute(text("INSERT INTO menu_items (id) VALUES (1)"))
        await session.execute(text("INSERT INTO menu_items (id) VALUES (2)"))
        await session.execute(text("INSERT INTO menu_items (id) VALUES (3)"))
        session.add_all(
            [
                OrderItem(
                    id=1,
                    order_id=1,
                    item_id=1,
                    name_snapshot="m1",
                    price_snapshot=1,
                    qty=1,
                    status="in_progress",
                ),
                OrderItem(
                    id=2,
                    order_id=2,
                    item_id=2,
                    name_snapshot="m2",
                    price_snapshot=1,
                    qty=1,
                    status="in_progress",
                ),
                OrderItem(
                    id=3,
                    order_id=3,
                    item_id=3,
                    name_snapshot="m3",
                    price_snapshot=1,
                    qty=1,
                    status="in_progress",
                ),
            ]
        )
        session.add(AlertRule(event="kds.sla_breach", channel="console", target="t"))
        session.add(
            AlertRule(event="kds.sla_breach.owner", channel="console", target="o")
        )
        session.add_all(
            [
                AuditTenant(
                    actor="chef",
                    action="progress_item",
                    at=now - timedelta(seconds=5),
                    meta={"path": f"/api/outlet/{tenant_id}/kds/item/1/progress"},
                ),
                AuditTenant(
                    actor="chef",
                    action="progress_item",
                    at=now - timedelta(seconds=10),
                    meta={"path": f"/api/outlet/{tenant_id}/kds/item/2/progress"},
                ),
                AuditTenant(
                    actor="chef",
                    action="progress_item",
                    at=now - timedelta(seconds=20),
                    meta={"path": f"/api/outlet/{tenant_id}/kds/item/3/progress"},
                ),
            ]
        )
        await session.commit()

    spec = importlib.util.spec_from_file_location(
        "kds_sla_watch", ROOT / "scripts/kds_sla_watch.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    breaches = await mod.scan(tenant_id)
    assert breaches == 3

    async with TenantSession() as session:
        rows = await session.execute(select(NotificationOutbox))
        events = rows.scalars().all()
        assert len(events) == 4
        owner = [e for e in events if e.event == "kds.sla_breach.owner"][0]
        assert owner.payload["items"] == [3, 2, 1]
        assert owner.payload["tables"] == [2, 1]

    await tenant_engine.dispose()
    await master_engine.dispose()
