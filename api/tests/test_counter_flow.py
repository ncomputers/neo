import pathlib
import sys

import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app
from api.app import main as app_main
from api.app import routes_counter
from api.app.models_tenant import Base, Category, MenuItem, Counter

app.state.redis = fakeredis.aioredis.FakeRedis()


class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture(scope="module", autouse=True)
def _setup_teardown():
    original = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()
    yield
    app_main.subscription_guard = original
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_counter_order_delivered_invoice():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as session:
        session.add(Category(id=1, name="Snacks", sort=1))
        session.add(MenuItem(id=1, category_id=1, name="Tea", price=10, is_veg=False))
        session.add(Counter(id=1, code="C1", qr_token="ctr1"))
        await session.commit()

    async def _tenant_id() -> str:
        return "demo"

    async def _session(tenant_id: str = "demo"):
        async with Session() as session:
            yield session

    app.dependency_overrides[routes_counter.get_tenant_id] = _tenant_id
    app.dependency_overrides[routes_counter.get_tenant_session] = _session
    app.dependency_overrides[routes_counter.get_session_from_path] = _session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        menu_resp = await client.get("/c/ctr1/menu")
        assert menu_resp.status_code == 200
        assert menu_resp.json()["ok"] is True
        item_id = menu_resp.json()["data"]["items"][0]["id"]

        order_resp = await client.post(
            "/c/ctr1/order",
            headers={"Idempotency-Key": "key1"},
            json={"items": [{"item_id": str(item_id), "qty": 1}]},
        )
        assert order_resp.status_code == 200
        assert order_resp.json()["ok"] is True
        order_id = order_resp.json()["data"]["order_id"]

        status_resp = await client.post(
            f"/api/outlet/demo/counters/{order_id}/status",
            json={"status": "delivered"},
        )
        assert status_resp.status_code == 200
        invoice_id = status_resp.json()["data"]["invoice_id"]
        assert invoice_id is not None

        pdf_resp = await client.get(f"/invoice/{invoice_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"].startswith("text/html")
