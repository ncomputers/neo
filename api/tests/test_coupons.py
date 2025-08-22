import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest

from api.app.services import billing_service
from api.app import models_tenant
from api.app.repos_sqlalchemy import invoices_repo_sql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from decimal import Decimal
from contextlib import asynccontextmanager


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_non_stackable_coupons_rejected():
    items = [{"price": 100}]
    c1 = {"code": "A", "percent": 10, "is_stackable": False}
    c2 = {"code": "B", "flat": 5, "is_stackable": False}
    with pytest.raises(ValueError) as exc:
        billing_service.compute_bill(items, "unreg", coupons=[c1, c2])
    assert "cannot be stacked" in str(exc.value)


def test_stackable_coupons_with_cap():
    items = [{"price": 200}]
    c1 = {"code": "C1", "percent": 5, "is_stackable": True, "max_discount": 15}
    c2 = {"code": "C2", "percent": 5, "is_stackable": True}
    bill = billing_service.compute_bill(items, "unreg", coupons=[c1, c2])
    assert bill["applied_coupons"] == ["C1", "C2"]
    assert bill["effective_discount"] == 15.0
    assert bill["total"] == 185.0


@pytest.mark.anyio
async def test_invoice_persists_coupon_details(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @asynccontextmanager
    async def fake_master_session():
        class Dummy:
            async def get(self, model, tenant_id):
                class T:
                    invoice_prefix = "INV"
                    invoice_reset = "never"

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

        coupons = [
            {"code": "C1", "percent": 5, "is_stackable": True},
            {
                "code": "C2",
                "percent": 5,
                "is_stackable": True,
                "max_discount": 5,
            },
        ]

        inv_id = await invoices_repo_sql.generate_invoice(
            session,
            1,
            "unreg",
            "nearest_1",
            tenant_id="T",
            tip=0,
            coupons=coupons,
        )
        await session.commit()
        invoice = await session.get(models_tenant.Invoice, inv_id)
        assert invoice.bill_json["applied_coupons"] == ["C1", "C2"]
        assert invoice.bill_json["effective_discount"] == 5.0

    await engine.dispose()
