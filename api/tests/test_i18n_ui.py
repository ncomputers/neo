from __future__ import annotations

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from fastapi import FastAPI  # noqa: E402

from api.app import routes_guest_menu  # noqa: E402
from api.app.deps.tenant import get_tenant_id as header_tenant_id  # noqa: E402
from api.app.middlewares import I18nMiddleware  # noqa: E402
from api.app.pdf import render as pdf_render  # noqa: E402
from api.app.repos_sqlalchemy import menu_repo_sql  # noqa: E402

app = FastAPI()
app.include_router(routes_guest_menu.router)
app.add_middleware(I18nMiddleware)
app.state.redis = fakeredis.aioredis.FakeRedis()
app.state.enabled_langs = ["en", "hi", "gu"]
app.state.default_lang = "en"


async def _fake_get_tenant_session():
    class _DummySession:
        pass

    return _DummySession()


async def _fake_list_categories(self, session):
    return []


async def _fake_list_items(self, session, include_hidden: bool = False):
    return [
        {
            "id": 1,
            "category_id": 1,
            "name": "Tea",
            "price": 10.0,
            "name_i18n": {"hi": "चाय", "gu": "ચા"},
        }
    ]


async def _fake_menu_etag(self, session):
    return "etag"


@pytest.fixture(autouse=True)
def _override_deps(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.dependency_overrides[routes_guest_menu.get_tenant_id] = header_tenant_id
    app.dependency_overrides[
        routes_guest_menu.get_tenant_session
    ] = _fake_get_tenant_session
    monkeypatch.setattr(
        menu_repo_sql.MenuRepoSQL,
        "list_categories",
        _fake_list_categories,
    )
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _fake_list_items)
    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "menu_etag", _fake_menu_etag)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_query_lang_and_cookie_persist():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/g/T-001/menu?lang=hi", headers={"X-Tenant-ID": "demo"}
        )
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["items"][0]["name"] == "चाय"
        assert any(c.value == "hi" for c in client.cookies.jar if c.name == "glang")
        resp2 = await client.get("/g/T-001/menu", headers={"X-Tenant-ID": "demo"})
        body2 = resp2.json()
        assert body2["data"]["items"][0]["name"] == "चाय"


@pytest.mark.anyio
async def test_missing_translation_falls_back(monkeypatch):
    async def _items(self, session, include_hidden: bool = False):
        return [
            {
                "id": 1,
                "category_id": 1,
                "name": "Tea",
                "price": 10.0,
                "name_i18n": {"gu": "ચા"},
            }
        ]

    monkeypatch.setattr(menu_repo_sql.MenuRepoSQL, "list_items", _items)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/g/T-001/menu?lang=hi", headers={"X-Tenant-ID": "demo"}
        )
        body = resp.json()
        assert body["data"]["items"][0]["name"] == "Tea"


def test_invoice_labels_localized():
    invoice = {
        "number": "1",
        "items": [{"name": "Tea", "price": 10.0, "qty": 1}],
        "subtotal": 10.0,
        "tax_lines": [],
        "grand_total": 10.0,
        "gst_mode": "unreg",
        "bill_lang": "hi",
    }
    html_bytes, mimetype = pdf_render.render_invoice(invoice, size="80mm")
    assert mimetype == "text/html"
    html = html_bytes.decode("utf-8")
    assert "उप-योग" in html
    assert "कुल" in html


@pytest.mark.anyio
async def test_query_overrides_cookie():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("glang", "gu")
        resp = await client.get(
            "/g/T-001/menu?lang=hi", headers={"X-Tenant-ID": "demo"}
        )
        body = resp.json()
        assert body["data"]["items"][0]["name"] == "चाय"
        assert any(c.value == "hi" for c in client.cookies.jar if c.name == "glang")
