from __future__ import annotations

import pathlib
import sys
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))
import os
os.environ.setdefault("POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./{tenant_id}.db")

from api.app import auth
from api.app.middlewares.i18n_mw import I18nMiddleware
from api.app.models_tenant import Category, MenuItem, TenantMeta
from api.app.routes_menu_i18n import router as i18n_router
import api.app.routes_menu_i18n as routes_menu_i18n
from api.app.utils.responses import ok
from api.tests.conftest_tenant import tenant_session  # noqa: F401


@pytest.fixture
def app(tenant_session, monkeypatch):
    app = FastAPI()
    app.include_router(i18n_router)
    app.add_middleware(I18nMiddleware)

    class DummyUser:
        username = "tester"
        role = "super_admin"

    app.dependency_overrides[auth.get_current_user] = lambda: DummyUser()

    @asynccontextmanager
    async def _fake_session(_tenant_id: str):
        yield tenant_session

    monkeypatch.setattr(routes_menu_i18n, "_session", _fake_session)
    return app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_import_valid_and_invalid_lang(app):
    transport = ASGITransport(app=app)
    async with tenant_session_context(app) as session:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # prepare DB
            cat = Category(id=1, name="Beverages", sort=1)
            item = MenuItem(id=1, category_id=1, name="Tea", price=10)
            meta = TenantMeta(id=1, default_lang="en", enabled_langs=["en", "hi"])
            session.add_all([cat, item, meta])
            await session.commit()
            csv_data = (
                "item_id,lang,name,description\n"
                "1,hi,Chai,Hindi tea\n"
                "1,zz,Bad,Bad\n"
            )
            files = {"file": ("t.csv", csv_data, "text/csv")}
            resp = await client.post("/api/outlet/demo/menu/i18n/import", files=files)
            assert resp.status_code == 200
            body = resp.json()["data"]
            assert body["updated_rows"] == 1
            assert body["skipped"] == 1
            assert body["errors"]
            item = await session.get(MenuItem, 1)
            assert item.name_i18n["hi"] == "Chai"
            assert "zz" not in item.name_i18n


@pytest.mark.anyio
async def test_export_returns_requested_langs(app):
    transport = ASGITransport(app=app)
    async with tenant_session_context(app) as session:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            cat = Category(id=1, name="Beverages", sort=1)
            item = MenuItem(
                id=1,
                category_id=1,
                name="Tea",
                price=10,
                name_i18n={"hi": "Chai", "gu": "Chaa"},
            )
            meta = TenantMeta(id=1, default_lang="en", enabled_langs=["en", "hi", "gu"])
            session.add_all([cat, item, meta])
            await session.commit()
            resp = await client.get(
                "/api/outlet/demo/menu/i18n/export?langs=hi",
            )
            assert resp.status_code == 200
            text = resp.text
            lines = text.strip().splitlines()
            assert lines[0] == "item_id,lang,name,description"
            assert len(lines) == 2
            assert lines[1].startswith("1,hi,Chai")


@pytest.mark.anyio
async def test_settings_rejects_invalid_default(app):
    transport = ASGITransport(app=app)
    async with tenant_session_context(app) as session:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            meta = TenantMeta(id=1, default_lang="en", enabled_langs=["en", "hi"])
            session.add(meta)
            await session.commit()
            payload = {"default_lang": "fr", "enabled_langs": ["en", "hi"]}
            resp = await client.patch(
                "/api/outlet/demo/settings/i18n", json=payload
            )
            assert resp.status_code == 400


@pytest.mark.anyio
async def test_middleware_query_overrides_cookie_and_persists():
    mapp = FastAPI()
    mapp.add_middleware(I18nMiddleware)
    mapp.state.enabled_langs = ["en", "hi", "gu"]
    mapp.state.default_lang = "en"

    @mapp.get("/")
    async def root(request: Request):
        return ok({"lang": request.state.lang})

    transport = ASGITransport(app=mapp)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("glang", "gu")
        resp1 = await client.get("/?lang=hi")
        assert resp1.json()["data"]["lang"] == "hi"
        resp2 = await client.get("/")
        assert resp2.json()["data"]["lang"] == "hi"


@asynccontextmanager
async def tenant_session_context(app: FastAPI):
    """Yield the session from patched _session."""
    # Retrieve the patched session from app fixture via dependency.
    # monkeypatch set on routes module ensures same session is used.
    from api.app.routes_menu_i18n import _session as patched_session
    from api.app.models_tenant import Base as TenantBase

    async with patched_session("demo") as session:
        engine = session.bind
        async with engine.begin() as conn:
            await conn.run_sync(TenantBase.metadata.create_all)
        yield session
