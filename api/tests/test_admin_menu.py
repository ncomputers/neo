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


@pytest.mark.anyio
async def test_etag_changes_after_item_toggle(monkeypatch) -> None:
    app.state.redis = fakeredis.aioredis.FakeRedis()
    item_id = "11111111-1111-1111-1111-111111111111"
    items = [{"id": item_id, "out_of_stock": False}]
    version = {"v": 0}

    async def fake_list_categories(self, session):
        return []

    async def fake_list_items(self, session, include_hidden=False):
        data = items if include_hidden else [i for i in items if not i["out_of_stock"]]
        return [{**i, "is_out_of_stock": i["out_of_stock"]} for i in data]

    async def fake_toggle_out_of_stock(self, session, item_id, flag):
        items[0]["out_of_stock"] = flag
        version["v"] += 1

    async def fake_menu_etag(self, session):
        return f"v{version['v']}"

    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_categories", fake_list_categories)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", fake_list_items)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "toggle_out_of_stock", fake_toggle_out_of_stock)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", fake_menu_etag)

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        class Dummy:
            pass

        yield Dummy()

    async def guest_session():
        class Dummy:
            pass

        return Dummy()

    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = guest_session
    monkeypatch.setattr(routes_admin_menu, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Tenant-ID": "demo"}
        resp = await client.get("/g/T-1/menu", headers=headers)
        etag0 = resp.headers["etag"]

        resp_cached = await client.get(
            "/g/T-1/menu", headers={"X-Tenant-ID": "demo", "If-None-Match": etag0}
        )
        assert resp_cached.status_code == 304

        await client.post(
            f"/api/outlet/demo/menu/item/{item_id}/out_of_stock",
            headers={"Authorization": f"Bearer {token}"},
            json={"flag": True},
        )

        resp2 = await client.get(
            "/g/T-1/menu", headers={"X-Tenant-ID": "demo", "If-None-Match": etag0}
        )
        assert resp2.status_code == 200
        etag1 = resp2.headers["etag"]
        assert etag1 != etag0

        resp3 = await client.get(
            "/g/T-1/menu", headers={"X-Tenant-ID": "demo", "If-None-Match": etag1}
        )
        assert resp3.status_code == 304

    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_toggle_hides_item(monkeypatch) -> None:
    app.state.redis = fakeredis.aioredis.FakeRedis()
    item_id = "11111111-1111-1111-1111-111111111111"
    items = [{"id": item_id, "out_of_stock": False}]

    async def fake_list_categories(self, session):
        return []

    async def fake_list_items(self, session, include_hidden=False):
        data = items if include_hidden else [i for i in items if not i["out_of_stock"]]
        return [{**i, "is_out_of_stock": i["out_of_stock"]} for i in data]

    async def fake_toggle_out_of_stock(self, session, item_id, flag):
        items[0]["out_of_stock"] = flag

    async def fake_menu_etag(self, session):
        return "etag" + ("1" if items[0]["out_of_stock"] else "0")

    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "list_categories", fake_list_categories
    )
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", fake_list_items)
    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "toggle_out_of_stock", fake_toggle_out_of_stock
    )
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", fake_menu_etag)

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
        assert resp.json()["data"]["items"] == [
            {"id": item_id, "out_of_stock": False}
        ]

        toggle = await client.post(
            f"/api/outlet/demo/menu/item/{item_id}/out_of_stock",
            headers={"Authorization": f"Bearer {token}"},
            json={"flag": True},
        )
        assert toggle.status_code == 200
        assert toggle.json()["data"] == [
            {"id": item_id, "out_of_stock": True, "is_out_of_stock": True}
        ]

        resp2 = await client.get("/g/T-1/menu", headers=headers)
        assert resp2.json()["data"]["items"] == []


@pytest.mark.anyio
async def test_menu_conditional_request_returns_304(monkeypatch) -> None:
    app.state.redis = fakeredis.aioredis.FakeRedis()
    async def fake_list_categories(self, session):
        return []

    async def fake_list_items(self, session, include_hidden=False):
        return []

    async def fake_menu_etag(self, session):
        return "etag"

    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_categories", fake_list_categories)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", fake_list_items)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", fake_menu_etag)

    async def guest_session():
        class Dummy:
            pass

        return Dummy()

    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = guest_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Tenant-ID": "demo"}
        resp = await client.get("/g/T-1/menu", headers=headers)
        assert resp.status_code == 200
        etag = resp.headers["etag"]
        resp2 = await client.get(
            "/g/T-1/menu", headers={"X-Tenant-ID": "demo", "If-None-Match": etag}
        )
        assert resp2.status_code == 304
        assert resp2.content == b""

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_menu_cache_invalidation_after_toggle(monkeypatch) -> None:
    app.state.redis = fakeredis.aioredis.FakeRedis()
    item_id = "11111111-1111-1111-1111-111111111111"
    items = [{"id": item_id, "out_of_stock": False}]
    calls = {"list_items": 0}

    async def fake_list_categories(self, session):
        return []

    async def fake_list_items(self, session, include_hidden=False):
        calls["list_items"] += 1
        data = items if include_hidden else [i for i in items if not i["out_of_stock"]]
        return [{**i, "is_out_of_stock": i["out_of_stock"]} for i in data]

    async def fake_toggle_out_of_stock(self, session, item_id, flag):
        items[0]["out_of_stock"] = flag

    async def fake_menu_etag(self, session):
        return "etag" + ("1" if items[0]["out_of_stock"] else "0")

    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_categories", fake_list_categories)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", fake_list_items)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "toggle_out_of_stock", fake_toggle_out_of_stock)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", fake_menu_etag)

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        class Dummy:
            pass

        yield Dummy()

    async def guest_session():
        class Dummy:
            pass

        return Dummy()

    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = guest_session
    monkeypatch.setattr(routes_admin_menu, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Tenant-ID": "demo"}
        resp1 = await client.get("/g/T-1/menu", headers=headers)
        assert calls["list_items"] == 1
        resp2 = await client.get("/g/T-1/menu", headers=headers)
        assert calls["list_items"] == 1
        await client.post(
            f"/api/outlet/demo/menu/item/{item_id}/out_of_stock",
            headers={"Authorization": f"Bearer {token}"},
            json={"flag": True},
        )
        resp3 = await client.get("/g/T-1/menu", headers=headers)
        assert calls["list_items"] == 3
        assert resp3.json()["data"]["items"] == []

    app.dependency_overrides.clear()
