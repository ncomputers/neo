import asyncio
import pathlib
import re
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.app.middlewares.security import SecurityMiddleware
from api.app.models_tenant import Base, Category, Counter, MenuItem
from api.app.repos_sqlalchemy import counter_orders_repo_sql
from api.app.routes_kot import get_session_from_path, router


async def _setup_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        session.add(Category(id=1, name="Snacks", sort=1))
        session.add(MenuItem(id=1, category_id=1, name="Tea", price=10, is_veg=False))
        session.add(Counter(id=1, code="C1", qr_token="ctr1"))
        await session.commit()
        order_id = await counter_orders_repo_sql.create_order(
            session, "ctr1", [{"item_id": "1", "qty": 2}]
        )
    return Session, order_id


Session, order_id = asyncio.run(_setup_db())


async def _session_dep(tenant_id: str):
    async with Session() as session:
        yield session


def test_kot_route_html_fallback():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_session_from_path] = _session_dep
    client = TestClient(app)
    resp = client.get(f"/api/outlet/demo/kot/{order_id}.pdf?size=80mm")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Tea" in resp.text
    assert ">2<" in resp.text
    assert "C1" in resp.text
    csp = resp.headers["content-security-policy"]
    m = re.search(r"nonce-([^']+)'", csp)
    assert m is not None
    nonce = m.group(1)
    assert f'nonce="{nonce}"' in resp.text
