import importlib
import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.repos_sqlalchemy import menu_repo_sql
from api.app import routes_guest_menu

async def _fake_get_tenant_session(tenant_id: str):
    class Dummy:
        pass

    return Dummy()

async def _fake_list_categories(self, session):
    return []

async def _fake_list_items(self, session, include_hidden: bool = False):
    return []

async def _fake_menu_etag(self, session):
    return "etag"


def test_guest_page_headers(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    monkeypatch.setenv("DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    from api.app import main as app_main

    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()

    app_main.app.dependency_overrides[routes_guest_menu.get_tenant_id] = (
        lambda table_token: "demo"
    )
    app_main.app.dependency_overrides[
        routes_guest_menu.get_tenant_session
    ] = _fake_get_tenant_session
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_categories", _fake_list_categories)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _fake_list_items)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", _fake_menu_etag)

    client = TestClient(app_main.app)
    resp = client.get(
        "/g/T-001/menu",
        headers={"Origin": "https://allowed.com", "X-Tenant-ID": "demo"},
    )
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("access-control-allow-origin") == "https://allowed.com"

    app_main.app.dependency_overrides.clear()
