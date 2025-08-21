import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport

from api.app import main as app_main
from api.app.main import app
from api.app import routes_admin_menu, routes_guest_menu
from api.app.auth import create_access_token
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from api.app.repos_sqlalchemy import menu_repo_sql
from contextlib import asynccontextmanager

app.state.redis = fakeredis.aioredis.FakeRedis()


class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture(scope="module", autouse=True)
def _setup_teardown():
    original_guard = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()
    yield
    app_main.subscription_guard = original_guard
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_toggle_hides_item(monkeypatch) -> None:
    item_id = "11111111-1111-1111-1111-111111111111"
    items = [{"id": item_id, "out_of_stock": False}]

    async def fake_list_categories(self, session):
        return []

    async def fake_list_items(self, session, include_hidden=False):
        if include_hidden:
            return items
        return [i for i in items if not i["out_of_stock"]]

    async def fake_toggle_out_of_stock(self, session, item_id, flag):
        items[0]["out_of_stock"] = flag

    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "list_categories", fake_list_categories
    )
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", fake_list_items)
    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "toggle_out_of_stock", fake_toggle_out_of_stock
    )

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        class Dummy:
            pass

        yield Dummy()

    monkeypatch.setattr(routes_admin_menu, "_session", fake_session)

    async def guest_session():
        class Dummy:
            pass

        return Dummy()

    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = guest_session

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Tenant-ID": "demo"}
        resp = await client.get("/g/T-1/menu", headers=headers)
        assert resp.json()["data"]["items"] == [{"id": item_id, "out_of_stock": False}]

        toggle = await client.post(
            f"/api/outlet/demo/menu/item/{item_id}/out_of_stock",
            headers={"Authorization": f"Bearer {token}"},
            json={"flag": True},
        )
        assert toggle.status_code == 200

        resp2 = await client.get("/g/T-1/menu", headers=headers)
        assert resp2.json()["data"]["items"] == []
