"""Tests for order void approval workflow."""

# flake8: noqa

import pathlib
import sys
from decimal import Decimal

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.app import routes_voids
from api.app.auth import User
from api.app.db import SessionLocal
from api.app.models_tenant import (
    AuditTenant,
    Base,
    Invoice,
    Order,
    OrderItem,
    OrderStatus,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_request_approve_void() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as session:
        order = Order(id=1, table_id=1, status=OrderStatus.NEW)
        session.add(order)
        session.add(
            OrderItem(
                order_id=1,
                item_id=1,
                name_snapshot="Tea",
                price_snapshot=50,
                qty=1,
                status=OrderStatus.NEW.value,
            )
        )
        invoice = Invoice(
            order_group_id=1,
            number="INV-1",
            bill_json={"subtotal": 50.0, "total": 50.0},
            total=Decimal("50.0"),
        )
        session.add(invoice)
        await session.commit()
        order_id = 1
        invoice_id = invoice.id

    async def _session(tenant_id: str = "demo"):
        async with Session() as session:
            yield session

    app = FastAPI()
    app.include_router(routes_voids.router)
    app.dependency_overrides[routes_voids.get_session_from_path] = _session

    async def _guard() -> User:
        return User(username="mgr", role="manager")

    app.dependency_overrides[routes_voids.manager_guard] = _guard
    app.state.redis = fakeredis.aioredis.FakeRedis()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.post(
            f"/api/outlet/demo/orders/{order_id}/void/request",
            json={"reason": "mistake"},
        )
        assert resp1.status_code == 200
        resp2 = await client.post(
            f"/api/outlet/demo/orders/{order_id}/void/approve",
        )
        assert resp2.status_code == 200

    async with Session() as session:
        updated = await session.get(Invoice, invoice_id)
        assert float(updated.total) == 0.0

    with SessionLocal() as session:
        actions = [row.action for row in session.query(AuditTenant).all()]
        assert "order.void.request" in actions
        assert "order.void.approve" in actions
