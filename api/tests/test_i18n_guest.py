from __future__ import annotations

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport

from api.app.main import app
from api.app.deps.tenant import get_tenant_id as header_tenant_id
from api.app import routes_guest_menu
from api.app.repos_sqlalchemy import menu_repo_sql


app.state.redis = fakeredis.aioredis.FakeRedis()


async def _fake_get_tenant_session():
    class _DummySession:
        pass

    return _DummySession()


async def _fake_list_categories(self, session):
    return []


async def _fake_list_items(self, session, include_hidden: bool = False):
    return []


async def _fake_menu_etag(self, session):
    return "etag"


@pytest.fixture(autouse=True)
def _override_deps():
    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[routes_guest_menu.get_tenant_session] = _fake_get_tenant_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_accept_language_hindi_returns_hindi_labels(monkeypatch):
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_categories", _fake_list_categories)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _fake_list_items)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", _fake_menu_etag)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/g/T-001/menu",
            headers={"X-Tenant-ID": "demo", "Accept-Language": "hi"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["labels"]["order"] == "ऑर्डर करें"

