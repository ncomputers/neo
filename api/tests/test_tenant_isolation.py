import pathlib
import sys
from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from contextlib import asynccontextmanager

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import db as app_db  # noqa: E402
sys.modules.setdefault("db", app_db)
from api.app import domain as app_domain  # noqa: E402
sys.modules.setdefault("domain", app_domain)
from api.app import models_tenant as app_models_tenant  # noqa: E402
sys.modules.setdefault("models_tenant", app_models_tenant)
from api.app import repos_sqlalchemy as app_repos_sqlalchemy  # noqa: E402
sys.modules.setdefault("repos_sqlalchemy", app_repos_sqlalchemy)
from api.app import utils as app_utils  # noqa: E402
sys.modules.setdefault("utils", app_utils)

from api.app import routes_exports  # noqa: E402
from api.app.repos_sqlalchemy import invoices_repo_sql  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402
from api.app import models_tenant  # noqa: E402
import os
from uuid import uuid4

os.environ.setdefault("POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_session() -> AsyncSession:
    tenant_id = "t_" + uuid4().hex[:8]
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()
        db_path = engine.url.database
        if db_path and os.path.exists(db_path):
            os.remove(db_path)


app_exports = FastAPI()
app_exports.include_router(routes_exports.router)


@pytest.mark.anyio
async def test_repo_guards_enforce_tenant(tenant_session):
    """Direct repo helpers should reject cross-tenant sessions."""
    with pytest.raises(PermissionError):
        await invoices_repo_sql.list_day(tenant_session, date.today(), "UTC", "other")


@pytest.mark.anyio
async def test_export_cross_tenant_forbidden(tenant_session, monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield tenant_session
    monkeypatch.setattr(routes_exports, "_session", fake_session)

    transport = ASGITransport(app=app_exports)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/other/exports/daily?start=2024-01-01&end=2024-01-01"
        )
        assert resp.status_code == 403
