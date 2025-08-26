import hashlib
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

import config
from api.app import routes_guest_menu
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from api.app.repos_sqlalchemy import menu_repo_sql
from fastapi import Depends


async def _fake_get_session(tenant_id: str = Depends(header_tenant_id)):
    class _Dummy:
        pass

    return _Dummy()


def test_menu_ab_allocation_and_exposure(monkeypatch):
    monkeypatch.setenv("AB_TESTS_ENABLED", "1")
    config.get_settings.cache_clear()
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.include_router(routes_guest_menu.router)
    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = _fake_get_session

    async def _fake_menu_etag(self, session):
        return "etag"

    async def _fake_list_categories(self, session):
        return []

    async def _fake_list_items(self, session):
        return [{"id": 1}]

    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", _fake_menu_etag)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_categories", _fake_list_categories)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _fake_list_items)

    captured = {}

    async def _post(self, url, json=None, **kwargs):  # type: ignore[override]
        captured["url"] = url
        captured["json"] = json
        class Resp:
            status_code = 200
        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", _post, raising=False)

    client = TestClient(app)
    resp = client.get("/g/T1/menu", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 200
    body = resp.json()
    variant = body["data"]["ab_variant"]
    expected = "B" if int(hashlib.md5(b"T1", usedforsecurity=False).hexdigest(), 16) % 2 else "A"
    assert variant == expected
    assert resp.cookies.get("ab_menu") == expected
    assert captured["url"].endswith("/analytics/ab")
    assert captured["json"]["variant"] == expected
