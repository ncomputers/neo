from __future__ import annotations

import asyncio
import importlib
import pathlib
import sys
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "api"))

from app.db.tenant import get_engine  # type: ignore
from app import models_tenant  # type: ignore
from app.models_tenant import Order, OrderItem, Invoice, Payment, OrderStatus  # type: ignore
from app.auth import create_access_token  # type: ignore
from tests._seed_tenant import seed_minimal_menu  # type: ignore


def test_digest_route(tmp_path, monkeypatch):
    tenant_id = "test_digest_api"
    dsn = f"sqlite+aiosqlite:///{tmp_path}/tenant_{tenant_id}.db"
    monkeypatch.setenv("POSTGRES_TENANT_DSN_TEMPLATE", dsn.replace(tenant_id, "{tenant_id}"))
    monkeypatch.setenv("DEFAULT_TZ", "UTC")

    async def seed():
        engine = get_engine(tenant_id)
        async with engine.begin() as conn:
            await conn.run_sync(models_tenant.Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with Session() as session:
            ids = await seed_minimal_menu(session)
            order = Order(
                table_id=str(ids["table_id"]),
                status=OrderStatus.CONFIRMED,
                placed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(order)
            await session.flush()
            item = OrderItem(
                order_id=order.id,
                item_id=ids["veg_item_id"],
                name_snapshot="Veg Item",
                price_snapshot=100,
                qty=1,
                status="SERVED",
            )
            session.add(item)
            invoice = Invoice(
                order_group_id=order.id,
                number="INV1",
                bill_json={"subtotal": 100.0, "tax_breakup": {}, "total": 100.0},
                total=100.0,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(invoice)
            await session.flush()
            payment = Payment(
                invoice_id=invoice.id,
                mode="cash",
                amount=100.0,
                verified=True,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(payment)
            await session.commit()
        await engine.dispose()

    asyncio.run(seed())

    import api.app.main as app_main
    importlib.reload(app_main)
    app = app_main.app

    class DummyRedis:
        async def sismember(self, *args, **kwargs):
            return False

        async def incr(self, *args, **kwargs):
            return 0

        async def sadd(self, *args, **kwargs):
            return 0

    app.state.redis = DummyRedis()

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    client = TestClient(app)
    resp = client.post(
        f"/api/outlet/{tenant_id}/digest/run?date=2024-01-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] is True
    assert "console" in data["channels"]
