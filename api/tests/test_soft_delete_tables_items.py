import os
import pathlib
import sys
import types
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import fakeredis.aioredis
import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import case, select

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

from api.app.auth import create_access_token  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.models_tenant import MenuItem, Table  # noqa: E402
from api.app.routes_admin_menu import router as menu_router  # noqa: E402
from api.app.routes_guest_order import (  # noqa: E402
    router as order_router,
    get_tenant_id,
    get_tenant_session,
)
from api.app.routes_tables_map import router as tables_router  # noqa: E402
from api.app.repos_sqlalchemy import orders_repo_sql  # noqa: E402
from api.app.hooks import order_rejection  # noqa: E402

app = FastAPI()
app.include_router(tables_router)
app.include_router(menu_router)
app.include_router(order_router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@asynccontextmanager
async def fake_session(_tenant: str = "demo"):
    class Dummy:
        pass

    yield Dummy()


def _admin_headers() -> dict:
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_table_and_item_delete_restore_and_listing(monkeypatch):
    tenant_id = str(uuid.uuid4())
    table_code = "T1"
    table_id = uuid.uuid4()
    item_id = uuid.uuid4()

    with SessionLocal() as session:
        session.add(
            Table(
                id=table_id,
                tenant_id=uuid.UUID(tenant_id),
                name="T1",
                code=table_code,
                state="AVAILABLE",
            )
        )
        session.commit()

    items = [{"id": item_id, "deleted": False}]

    async def fake_list_items(self, session, include_hidden=False, include_deleted=False):
        data = items if include_deleted else [i for i in items if not i["deleted"]]
        return [{"id": i["id"]} for i in data]

    async def fake_soft_delete_item(self, session, iid):
        items[0]["deleted"] = True

    async def fake_restore_item(self, session, iid):
        items[0]["deleted"] = False

    @asynccontextmanager
    async def local_session(_tenant: str = "demo"):
        class Dummy:
            async def get(self, model, iid):
                for it in items:
                    if it["id"] == iid:
                        class Obj:
                            id = iid
                            name = "Item"
                            deleted_at = datetime.utcnow() if it["deleted"] else None

                        return Obj()

        yield Dummy()

    monkeypatch.setattr("api.app.routes_admin_menu._session", local_session)
    monkeypatch.setattr(
        "api.app.repos_sqlalchemy.menu_repo_sql.MenuRepoSQL.list_items", fake_list_items
    )
    monkeypatch.setattr(
        "api.app.repos_sqlalchemy.menu_repo_sql.MenuRepoSQL.soft_delete_item",
        fake_soft_delete_item,
    )
    monkeypatch.setattr(
        "api.app.repos_sqlalchemy.menu_repo_sql.MenuRepoSQL.restore_item",
        fake_restore_item,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/outlet/{tenant_id}/tables/map")
        assert any(t["code"] == table_code for t in resp.json()["data"])

        await client.patch(
            f"/api/outlet/{tenant_id}/tables/{table_code}/delete",
            headers=_admin_headers(),
        )
        resp = await client.get(f"/api/outlet/{tenant_id}/tables/map")
        assert all(t["code"] != table_code for t in resp.json()["data"])
        resp = await client.get(
            f"/api/outlet/{tenant_id}/tables/map?include_deleted=true"
        )
        assert any(t["code"] == table_code for t in resp.json()["data"])
        await client.post(
            f"/api/outlet/{tenant_id}/tables/{table_code}/restore",
            headers=_admin_headers(),
        )
        resp = await client.get(f"/api/outlet/{tenant_id}/tables/map")
        assert any(t["code"] == table_code for t in resp.json()["data"])

        resp = await client.get(
            f"/api/outlet/{tenant_id}/menu/items", headers=_admin_headers()
        )
        assert resp.json()["data"] == [{"id": str(item_id)}]
        await client.patch(
            f"/api/outlet/{tenant_id}/menu/items/{item_id}/delete",
            headers=_admin_headers(),
        )
        resp = await client.get(
            f"/api/outlet/{tenant_id}/menu/items", headers=_admin_headers()
        )
        assert resp.json()["data"] == []
        resp = await client.get(
            f"/api/outlet/{tenant_id}/menu/items?include_deleted=true",
            headers=_admin_headers(),
        )
        assert resp.json()["data"] == [{"id": str(item_id)}]
        await client.post(
            f"/api/outlet/{tenant_id}/menu/items/{item_id}/restore",
            headers=_admin_headers(),
        )
        resp = await client.get(
            f"/api/outlet/{tenant_id}/menu/items", headers=_admin_headers()
        )
        assert resp.json()["data"] == [{"id": str(item_id)}]


@pytest.mark.anyio
async def test_order_guard_for_deleted_resources(monkeypatch):
    app.dependency_overrides[get_tenant_id] = lambda table_token: "demo"
    app.dependency_overrides[get_tenant_session] = fake_session

    async def fake_on_rejected(tenant_id, ip, redis):
        return None

    monkeypatch.setattr(order_rejection, "on_rejected", fake_on_rejected)

    table_deleted = True
    item_deleted = False

    async def fake_create_order(session, token, lines):
        if table_deleted:
            raise HTTPException(
                status_code=403,
                detail={"code": "GONE_RESOURCE", "message": "Table is inactive/deleted"},
            )
        if item_deleted:
            raise HTTPException(
                status_code=403,
                detail={"code": "GONE_RESOURCE", "message": "Menu item is inactive/deleted"},
            )
        return 1

    monkeypatch.setattr(orders_repo_sql, "create_order", fake_create_order)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/g/t1/order", json={"items": [{"item_id": "1", "qty": 1}]}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == {
            "code": "GONE_RESOURCE",
            "message": "Table is inactive/deleted",
        }

        table_deleted = False
        item_deleted = True
        resp = await client.post(
            "/g/t1/order", json={"items": [{"item_id": "1", "qty": 1}]}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == {
            "code": "GONE_RESOURCE",
            "message": "Menu item is inactive/deleted",
        }


def test_export_status_column():
    with SessionLocal() as session:
        now = datetime.utcnow()
        session.add(MenuItem(id=1, category_id=1, name="A", price=1))
        session.add(MenuItem(id=2, category_id=1, name="B", price=1, deleted_at=now))
        session.commit()
        stmt = select(
            MenuItem.id,
            case((MenuItem.deleted_at.isnot(None), "deleted"), else_="active").label(
                "status"
            ),
        ).order_by(MenuItem.id)
        rows = session.execute(stmt).all()
        assert rows[0].status == "active"
        assert rows[1].status == "deleted"

