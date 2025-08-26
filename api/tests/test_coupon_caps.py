import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager

from api.app.services import billing_service
from api.app import models_tenant
from api.app.repos_sqlalchemy import invoices_repo_sql


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def session(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @asynccontextmanager
    async def fake_master_session():
        class Dummy:
            async def get(self, model, tenant_id):
                class T:
                    inv_prefix = "INV"
                    inv_reset = "never"

                return T()

            async def close(self):
                pass

        yield Dummy()

    monkeypatch.setattr(
        invoices_repo_sql, "get_master_session", fake_master_session
    )

    async with async_session() as session:
        await session.execute(
            text(
                "INSERT INTO tables (id, tenant_id, name, code, status, state, pos_x, pos_y) "
                "VALUES (1, 't', 'T1', 'T1', 'available', 'AVAILABLE', 0, 0)"
            )
        )
        await session.execute(
            text(
                "INSERT INTO orders (id, table_id, status) VALUES (1, 1, 'placed')"
            )
        )
        category = models_tenant.Category(name="C", sort=1)
        session.add(category)
        await session.flush()
        item = models_tenant.MenuItem(
            category_id=category.id,
            name="Tea",
            price=Decimal("100"),
            gst_rate=0,
        )
        session.add(item)
        await session.flush()
        session.add(
            models_tenant.OrderItem(
                order_id=1,
                item_id=item.id,
                name_snapshot="Tea",
                price_snapshot=Decimal("100"),
                qty=1,
                status="placed",
            )
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.anyio
async def test_per_guest_cap(session):
    coupon = models_tenant.Coupon(
        code="ONCE",
        percent=10,
        is_stackable=True,
        per_guest_cap=1,
    )
    session.add(coupon)
    await session.commit()

    coupons = [{"code": "ONCE", "percent": 10, "is_stackable": True}]
    await invoices_repo_sql.generate_invoice(
        session,
        1,
        "unreg",
        "nearest_1",
        tenant_id="T",
        tip=0,
        coupons=coupons,
        guest_id=1,
        outlet_id=1,
    )

    with pytest.raises(billing_service.CouponError) as exc:
        await invoices_repo_sql.generate_invoice(
            session,
            1,
            "unreg",
            "nearest_1",
            tenant_id="T",
            tip=0,
            coupons=coupons,
            guest_id=1,
            outlet_id=1,
        )
    assert exc.value.code == "GUEST_CAP"


@pytest.mark.anyio
async def test_time_window_enforced(session):
    future = datetime.now(timezone.utc) + timedelta(days=1)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    c_future = models_tenant.Coupon(
        code="FUT",
        percent=10,
        is_stackable=True,
        valid_from=future,
    )
    c_past = models_tenant.Coupon(
        code="PAST",
        percent=10,
        is_stackable=True,
        valid_to=past,
    )
    session.add_all([c_future, c_past])
    await session.commit()

    with pytest.raises(billing_service.CouponError) as exc:
        await invoices_repo_sql.generate_invoice(
            session,
            1,
            "unreg",
            "nearest_1",
            tenant_id="T",
            tip=0,
            coupons=[{"code": "FUT", "percent": 10, "is_stackable": True}],
            guest_id=1,
            outlet_id=1,
        )
    assert exc.value.code == "NOT_ACTIVE"

    with pytest.raises(billing_service.CouponError) as exc:
        await invoices_repo_sql.generate_invoice(
            session,
            1,
            "unreg",
            "nearest_1",
            tenant_id="T",
            tip=0,
            coupons=[{"code": "PAST", "percent": 10, "is_stackable": True}],
            guest_id=1,
            outlet_id=1,
        )
    assert exc.value.code == "EXPIRED"
