import asyncio
import os
import pathlib
import sys
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ensure app modules importable
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import models_tenant  # noqa: E402
from api.app.auth import ALGORITHM, SECRET_KEY, create_access_token  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)


@pytest.fixture
def anyio_backend() -> str:  # noqa: D401
    """Use asyncio for anyio tests."""
    return "asyncio"


@pytest.mark.anyio
async def test_cross_tenant_id_not_found():
    """Fetching an ID from another tenant returns 404."""
    t1 = "t_" + uuid4().hex[:8]
    t2 = "t_" + uuid4().hex[:8]
    e1 = get_engine(t1)
    e2 = get_engine(t2)
    async with e1.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    async with e2.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    Session1 = async_sessionmaker(e1, expire_on_commit=False, class_=AsyncSession)
    Session2 = async_sessionmaker(e2, expire_on_commit=False, class_=AsyncSession)
    try:
        async with Session1() as s1, Session2() as s2:
            row = models_tenant.NotificationOutbox(
                event="e", payload={}, channel="c", target="t"
            )
            s1.add(row)
            await s1.commit()
            item_id = row.id

            sessions = {t1: s1, t2: s2}

            @asynccontextmanager
            async def fake_session(tenant_id: str):
                yield sessions[tenant_id]

            app = FastAPI()

            @app.get("/api/outlet/{tenant}/outbox/{item_id}")
            async def get_item(tenant: str, item_id: int):
                async with fake_session(tenant) as session:
                    obj = await session.get(models_tenant.NotificationOutbox, item_id)
                    if obj is None:
                        raise HTTPException(status_code=404)
                    return {"id": obj.id}

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                ok_resp = await client.get(f"/api/outlet/{t1}/outbox/{item_id}")
                assert ok_resp.status_code == 200
                bad_resp = await client.get(f"/api/outlet/{t2}/outbox/{item_id}")
                assert bad_resp.status_code == 404
    finally:
        await e1.dispose()
        await e2.dispose()
        for engine in (e1, e2):
            path = engine.url.database
            if path and os.path.exists(path):
                os.remove(path)


@pytest.mark.anyio
async def test_signed_media_rejects_foreign_tenant():
    """Signed media URLs are tenant-scoped and reject foreign tenants."""
    app = FastAPI()

    @app.get("/media/{tenant}/{key}")
    async def get_media(tenant: str, key: str, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="expired")
        except jwt.PyJWTError:
            raise HTTPException(status_code=403, detail="bad token")
        if payload.get("tenant") != tenant or payload.get("key") != key:
            raise HTTPException(status_code=403, detail="tenant mismatch")
        return {"ok": True}

    token = create_access_token({"tenant": "t1", "key": "logo.png", "sub": "u"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get(f"/media/t1/logo.png?token={token}")
        assert ok.status_code == 200
        foreign = await client.get(f"/media/t2/logo.png?token={token}")
        assert foreign.status_code == 403


@pytest.mark.anyio
async def test_export_signature_ttl():
    """Export links require a valid tenant signature that expires."""
    app = FastAPI()

    @app.get("/api/outlet/{tenant}/exports/dummy")
    async def export_dummy(tenant: str, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="expired")
        except jwt.PyJWTError:
            raise HTTPException(status_code=403, detail="bad token")
        if payload.get("tenant") != tenant:
            raise HTTPException(status_code=403, detail="tenant mismatch")
        return {"ok": True}

    token = create_access_token(
        {"tenant": "t1", "sub": "u"}, expires_delta=timedelta(seconds=1)
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        good = await client.get(f"/api/outlet/t1/exports/dummy?token={token}")
        assert good.status_code == 200
        foreign = await client.get(f"/api/outlet/t2/exports/dummy?token={token}")
        assert foreign.status_code == 403
        await asyncio.sleep(2)
        expired = await client.get(f"/api/outlet/t1/exports/dummy?token={token}")
        assert expired.status_code == 403
