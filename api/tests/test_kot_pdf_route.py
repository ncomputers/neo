import os
import pathlib
import sys
from contextlib import asynccontextmanager

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid import uuid4

from api.app import db as app_db  # noqa: E402

sys.modules.setdefault("db", app_db)  # noqa: E402

from api.app.routes_kot_pdf import router  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402
from api.app.models_tenant import Base, Order, OrderItem, OrderStatus  # noqa: E402

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_kot_pdf_route_returns_items(monkeypatch):
    tenant_id = "test_" + uuid4().hex[:8]
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        order = Order(table_id=1, status=OrderStatus.NEW)
        session.add(order)
        await session.flush()
        session.add_all(
            [
                OrderItem(
                    order_id=order.id,
                    item_id=1,
                    name_snapshot="Tea",
                    price_snapshot=10,
                    qty=2,
                    status="new",
                ),
                OrderItem(
                    order_id=order.id,
                    item_id=2,
                    name_snapshot="Coffee",
                    price_snapshot=15,
                    qty=1,
                    status="new",
                ),
            ]
        )
        await session.commit()

        @asynccontextmanager
        async def fake_session(_tenant: str):
            yield session

        monkeypatch.setattr("api.app.routes_kot_pdf._session", fake_session)

        app = FastAPI()
        app.include_router(router)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/outlet/{tenant_id}/kot/{order.id}.pdf?size=80mm"
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/html")
            body = resp.text
            assert "Tea" in body
            assert "2" in body
            assert "Coffee" in body
            assert "1" in body

    await engine.dispose()
    db_path = engine.url.database
    if db_path and os.path.exists(db_path):
        os.remove(db_path)
