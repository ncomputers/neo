import asyncio
import os
import pathlib
import sys
import types

import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

sys.modules.setdefault("PIL", types.ModuleType("PIL"))
sys.modules.setdefault("PIL.Image", types.ModuleType("Image"))
sys.modules.setdefault("PIL.ImageOps", types.ModuleType("ImageOps"))
sys.modules.setdefault(
    "api.app.services.printer_watchdog", types.ModuleType("printer_watchdog")
)

from fastapi import FastAPI

from api.app import routes_integrations_marketplace  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402

app = FastAPI()
app.include_router(routes_integrations_marketplace.router)

app.state.redis = fakeredis.aioredis.FakeRedis()


def test_list_marketplace():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/outlet/t1/integrations/marketplace",
                headers={"Authorization": f"Bearer {token}"},
            )
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    types_list = {item["type"] for item in resp.json()["data"]}
    assert {"google_sheets", "slack", "zoho_books"}.issubset(types_list)


@pytest.mark.parametrize("integration_type", ["slack", "google_sheets", "zoho_books"])
def test_connect_integration(monkeypatch, integration_type):
    routes_integrations_marketplace.TENANT_INTEGRATIONS.clear()
    report = {"allowed": True}

    async def fake_probe(url: str):
        return report

    monkeypatch.setattr(routes_integrations_marketplace, "probe_webhook", fake_probe)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/outlet/t1/integrations/connect",
                json={"type": integration_type, "url": "https://example.com/hook"},
                headers={"Authorization": f"Bearer {token}"},
            )
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["probe"] == report
    assert (
        routes_integrations_marketplace.TENANT_INTEGRATIONS["t1"][integration_type]["url"]
        == "https://example.com/hook"
    )


def test_connect_integration_tenant_isolation(monkeypatch):
    routes_integrations_marketplace.TENANT_INTEGRATIONS.clear()
    report = {"allowed": True}

    async def fake_probe(url: str):
        return report

    monkeypatch.setattr(routes_integrations_marketplace, "probe_webhook", fake_probe)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/outlet/t1/integrations/connect",
                json={"type": "slack", "url": "https://example.com/one"},
                headers={"Authorization": f"Bearer {token}"},
            )
            await client.post(
                "/api/outlet/t2/integrations/connect",
                json={"type": "slack", "url": "https://example.com/two"},
                headers={"Authorization": f"Bearer {token}"},
            )

    asyncio.run(_run())
    assert (
        routes_integrations_marketplace.TENANT_INTEGRATIONS["t1"]["slack"]["url"]
        == "https://example.com/one"
    )
    assert (
        routes_integrations_marketplace.TENANT_INTEGRATIONS["t2"]["slack"]["url"]
        == "https://example.com/two"
    )


@pytest.mark.parametrize(
    "warnings,detail",
    [
        (["tls_self_signed"], "Webhook has self-signed TLS certificate"),
        (["slow"], "Webhook responded too slowly"),
    ],
)
def test_connect_integration_with_warnings(monkeypatch, warnings, detail):
    routes_integrations_marketplace.TENANT_INTEGRATIONS.clear()
    report = {"allowed": True, "warnings": warnings}

    async def fake_probe(url: str):
        return report

    monkeypatch.setattr(routes_integrations_marketplace, "probe_webhook", fake_probe)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/outlet/t1/integrations/connect",
                json={"type": "slack", "url": "https://example.com/hook"},
                headers={"Authorization": f"Bearer {token}"},
            )

    resp = asyncio.run(_run())
    assert resp.status_code == 400
    assert resp.json()["detail"] == detail
