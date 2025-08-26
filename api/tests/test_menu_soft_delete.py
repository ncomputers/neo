import os
import pathlib
import sys
import types
from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

# stub modules required by imported code
_webhooks = types.ModuleType("routes_webhooks")
_webhooks.router = APIRouter()
sys.modules.setdefault("api.app.routes_webhooks", _webhooks)
_webhook_tools = types.ModuleType("routes_webhook_tools")
_webhook_tools.router = APIRouter()
sys.modules.setdefault("api.app.routes_webhook_tools", _webhook_tools)

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://u:p@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from api.app import routes_admin_menu  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.repos_sqlalchemy import menu_repo_sql  # noqa: E402
from api.app.routes_admin_menu import router as admin_menu_router  # noqa: E402

app = FastAPI()
app.include_router(admin_menu_router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_delete_and_restore_menu_item(monkeypatch) -> None:
    item_id = "11111111-1111-1111-1111-111111111111"
    items = [{"id": item_id, "deleted": False}]

    async def fake_list_items(
        self, session, include_hidden=False, include_deleted=False
    ):
        data = items if include_deleted else [i for i in items if not i["deleted"]]
        return [{"id": i["id"]} for i in data]

    async def fake_soft_delete_item(self, session, item_id):
        items[0]["deleted"] = True

    async def fake_restore_item(self, session, item_id):
        items[0]["deleted"] = False

    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", fake_list_items)
    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "soft_delete_item", fake_soft_delete_item
    )
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "restore_item", fake_restore_item)

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        class Dummy:
            async def get(self, model, item_id):
                class Item:
                    id = item_id
                    name = "foo"
                    deleted_at = None

                return Item()

        yield Dummy()

    monkeypatch.setattr(routes_admin_menu, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}
        resp1 = await client.get("/api/outlet/demo/menu/items", headers=headers)
        assert resp1.json()["data"] == [{"id": item_id}]
        await client.patch(
            f"/api/outlet/demo/menu/items/{item_id}/delete", headers=headers
        )
        resp2 = await client.get("/api/outlet/demo/menu/items", headers=headers)
        assert resp2.json()["data"] == []
        resp3 = await client.get(
            "/api/outlet/demo/menu/items?include_deleted=true", headers=headers
        )
        assert resp3.json()["data"] == [{"id": item_id}]
        await client.post(
            f"/api/outlet/demo/menu/items/{item_id}/restore", headers=headers
        )
        resp4 = await client.get("/api/outlet/demo/menu/items", headers=headers)
        assert resp4.json()["data"] == [{"id": item_id}]


@pytest.mark.anyio
async def test_delete_restore_nonexistent_item(monkeypatch) -> None:
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        class Dummy:
            async def execute(self, stmt):
                class Result:
                    rowcount = 0

                return Result()

        yield Dummy()

    monkeypatch.setattr(routes_admin_menu, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.patch(
            "/api/outlet/demo/menu/items/00000000-0000-0000-0000-000000000000/delete",
            headers=headers,
        )
        assert resp.status_code == 404
        resp = await client.post(
            "/api/outlet/demo/menu/items/00000000-0000-0000-0000-000000000000/restore",
            headers=headers,
        )
        assert resp.status_code == 404
