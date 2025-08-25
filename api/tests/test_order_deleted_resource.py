import os
import pathlib
import sys
import types
from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

# stub modules required by imported code
_webhooks = types.ModuleType("routes_webhooks")
_webhooks.router = APIRouter()
sys.modules.setdefault("api.app.routes_webhooks", _webhooks)
_webhook_tools = types.ModuleType("routes_webhook_tools")
_webhook_tools.router = APIRouter()
sys.modules.setdefault("api.app.routes_webhook_tools", _webhook_tools)

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://u:p@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from api.app import routes_guest_order, routes_counter  # noqa: E402
from api.app.hooks import order_rejection  # noqa: E402
from api.app.repos_sqlalchemy import (  # noqa: E402
    orders_repo_sql,
    counter_orders_repo_sql,
)

app = FastAPI()
app.include_router(routes_guest_order.router)
app.include_router(routes_counter.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@asynccontextmanager
async def fake_session(tenant_id: str = "demo"):
    class Dummy:
        pass

    yield Dummy()


@pytest.mark.anyio
async def test_order_on_deleted_resource_returns_403(monkeypatch) -> None:
    async def fake_create_order(session, token, lines):
        raise HTTPException(
            status_code=403,
            detail={"code": "GONE_RESOURCE", "message": "Menu item is inactive/deleted"},
        )

    async def fake_on_rejected(tenant_id, ip, redis):
        return None

    monkeypatch.setattr(orders_repo_sql, "create_order", fake_create_order)
    monkeypatch.setattr(counter_orders_repo_sql, "create_order", fake_create_order)
    monkeypatch.setattr(order_rejection, "on_rejected", fake_on_rejected)

    app.dependency_overrides[routes_guest_order.get_tenant_id] = (
        lambda table_token: "demo"
    )
    app.dependency_overrides[routes_guest_order.get_tenant_session] = fake_session
    app.dependency_overrides[routes_counter.get_tenant_id] = lambda: "demo"
    app.dependency_overrides[routes_counter.get_tenant_session] = fake_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.post(
            "/g/t1/order",
            json={"items": [{"item_id": "1", "qty": 1}]},
        )
        assert resp1.status_code == 403
        assert resp1.json()["detail"] == {
            "code": "GONE_RESOURCE",
            "message": "Menu item is inactive/deleted",
        }

        resp2 = await client.post(
            "/c/c1/order",
            json={"items": [{"item_id": "1", "qty": 1}]},
        )
        assert resp2.status_code == 403
        assert resp2.json()["detail"] == {
            "code": "GONE_RESOURCE",
            "message": "Menu item is inactive/deleted",
        }
