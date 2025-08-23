import importlib.util
import os
import pathlib
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from app.db.tenant import get_engine  # type: ignore
from app import models_tenant  # type: ignore
from app.models_tenant import (
    Order,
    OrderItem,
    Invoice,
    Payment,
    OrderStatus,
)
from tests._seed_tenant import seed_minimal_menu  # type: ignore

os.environ.setdefault("POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db")
os.environ.setdefault("DEFAULT_TZ", "UTC")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_setup(tmp_path):
    tenant_id = "test_digest"
    dsn = f"sqlite+aiosqlite:///{tmp_path}/tenant_{tenant_id}.db"
    os.environ["POSTGRES_TENANT_DSN_TEMPLATE"] = dsn.replace(tenant_id, "{tenant_id}")
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with Session() as session:
            ids = await seed_minimal_menu(session)
            order = Order(
                table_id=str(ids["table_id"]),
                status=OrderStatus.CONFIRMED,
                placed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(order)
            await session.flush()
            oi1 = OrderItem(
                order_id=order.id,
                item_id=ids["veg_item_id"],
                name_snapshot="Veg Item",
                price_snapshot=100,
                qty=2,
                status="SERVED",
            )
            oi2 = OrderItem(
                order_id=order.id,
                item_id=ids["non_veg_item_id"],
                name_snapshot="Non-Veg Item",
                price_snapshot=150,
                qty=1,
                status="SERVED",
            )
            session.add_all([oi1, oi2])
            invoice = Invoice(
                order_group_id=order.id,
                number="INV1",
                bill_json={"subtotal": 350.0, "tax_breakup": {}, "total": 350.0},
                total=350.0,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(invoice)
            await session.flush()
            p1 = Payment(
                invoice_id=invoice.id,
                mode="cash",
                amount=150.0,
                verified=True,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            p2 = Payment(
                invoice_id=invoice.id,
                mode="upi",
                amount=200.0,
                verified=True,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add_all([p1, p2])
            await session.commit()
        yield tenant_id
    finally:
        await engine.dispose()
        db_path = engine.url.database
        if db_path and os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.anyio
async def test_daily_digest_line(tenant_setup, capsys):
    tenant_id = tenant_setup
    spec = importlib.util.spec_from_file_location("daily_digest", "scripts/daily_digest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    await module.main(tenant_id, "2024-01-01")
    captured = capsys.readouterr()
    expected = (
        "2024-01-01 | orders=1 | sales=350.00 | avg_ticket=350.00 | "
        "top_items=Veg Item(2), Non-Veg Item(1) | payments=cash:150.00, upi:200.00"
    )
    assert captured.out.strip() == expected
