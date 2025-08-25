"""Tests for tenant support bundle export."""

from __future__ import annotations

import io
import pathlib
import sys
import zipfile
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.auth import create_access_token  # noqa: E402
from api.app.routes_support_bundle import router as support_router  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_support_bundle(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(support_router)

    async def fake_ready() -> dict:
        return {"ok": True}

    async def fake_version() -> dict:
        return {"sha": "abc", "built_at": "now"}

    monkeypatch.setattr("api.app.routes_support_bundle.ready", fake_ready)
    monkeypatch.setattr("api.app.routes_support_bundle.version", fake_version)

    class DummyTenant:
        licensed_tables = 5
        enable_hotel = True
        enable_counter = False
        license_limits = {"plan": "basic"}

    class DummySession:
        async def get(self, model, pk):
            return DummyTenant()

        async def close(self):
            pass

    @asynccontextmanager
    async def fake_get_session():
        yield DummySession()

    monkeypatch.setattr("api.app.routes_support_bundle.get_session", fake_get_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/outlet/demo/support/bundle.zip",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = set(zf.namelist())
        expected = {
            "env.txt",
            "health.json",
            "ready.json",
            "version.json",
            "config.json",
            "recent_audit.json",
        }
        assert expected.issubset(names)
