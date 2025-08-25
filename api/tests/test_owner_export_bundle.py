"""Tests for owner data portability export."""

from __future__ import annotations

import io
import pathlib
import sys
import zipfile
from contextlib import asynccontextmanager

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import routes_exports  # noqa: E402

app = FastAPI()
app.include_router(routes_exports.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_owner_export_bundle(monkeypatch):
    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield None

    monkeypatch.setattr(routes_exports, "_session", fake_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/outlet/demo/export/all.zip")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = set(zf.namelist())
        expected = {
            "menu.csv",
            "orders.csv",
            "invoices.csv",
            "payments.csv",
            "customers.csv",
            "settings.csv",
            "schema.json",
        }
        assert expected.issubset(names)
