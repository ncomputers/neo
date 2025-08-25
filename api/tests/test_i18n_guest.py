from __future__ import annotations

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from api.app import routes_guest_menu  # noqa: E402
from api.app.deps.tenant import get_tenant_id as header_tenant_id  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.middlewares import table_state_guard as tsg_module  # noqa: E402
from api.app.repos_sqlalchemy import menu_repo_sql  # noqa: E402
from api.app.utils.responses import ok  # noqa: E402

app.state.redis = fakeredis.aioredis.FakeRedis()


@app.post("/g/{table_token}/dummy")
async def _g_dummy(table_token: str):
    return ok({"dummy": True})


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
    app.dependency_overrides[
        routes_guest_menu.get_tenant_session
    ] = _fake_get_tenant_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_accept_language_hindi_returns_hindi_labels(monkeypatch):
    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "list_categories", _fake_list_categories
    )
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


@pytest.mark.anyio
async def test_accept_language_gujarati_returns_gujarati_labels(monkeypatch):
    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL, "list_categories", _fake_list_categories
    )
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _fake_list_items)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", _fake_menu_etag)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/g/T-001/menu",
            headers={"X-Tenant-ID": "demo", "Accept-Language": "gu"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["labels"]["order"] == "ઓર્ડર કરો"


@pytest.mark.anyio
async def test_table_locked_error_hindi(monkeypatch):
    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def query(self, model):
            class Query:
                def filter_by(self, **kwargs):
                    class Result:
                        def one_or_none(self):
                            class TableObj:
                                tenant_id = "t1"
                                state = "LOCKED"

                            return TableObj()

                    return Result()

            return Query()

        def get(self, model, pk):
            class TenantObj:
                default_language = "en"

            return TenantObj()

    monkeypatch.setattr(tsg_module, "SessionLocal", lambda: DummySession())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/g/T-001/dummy", headers={"Accept-Language": "hi"})
    assert resp.status_code == 423
    body = resp.json()
    assert body["error"]["code"] == "TABLE_LOCKED"
    assert body["error"]["message"] == "टेबल तैयार नहीं है"


@pytest.mark.anyio
async def test_table_locked_error_gujarati(monkeypatch):
    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def query(self, model):
            class Query:
                def filter_by(self, **kwargs):
                    class Result:
                        def one_or_none(self):
                            class TableObj:
                                tenant_id = "t1"
                                state = "LOCKED"

                            return TableObj()

                    return Result()

            return Query()

        def get(self, model, pk):
            class TenantObj:
                default_language = "en"

            return TenantObj()

    monkeypatch.setattr(tsg_module, "SessionLocal", lambda: DummySession())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/g/T-001/dummy", headers={"Accept-Language": "gu"})
    assert resp.status_code == 423
    body = resp.json()
    assert body["error"]["code"] == "TABLE_LOCKED"
    assert body["error"]["message"] == "ટેબલ તૈયાર નથી"
