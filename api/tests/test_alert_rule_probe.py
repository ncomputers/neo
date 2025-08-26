import asyncio
import pathlib
import sys
from contextlib import asynccontextmanager

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))  # noqa: E402

import importlib  # noqa: E402
import itertools  # noqa: E402
import os  # noqa: E402
import ssl  # noqa: E402
import types  # noqa: E402

from fastapi import APIRouter  # noqa: E402

os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

sys.modules.setdefault("PIL", types.ModuleType("PIL"))
sys.modules.setdefault("PIL.Image", types.ModuleType("Image"))
sys.modules.setdefault("PIL.ImageOps", types.ModuleType("ImageOps"))
menu_pkg = importlib.import_module("api.app.menu")
setattr(menu_pkg, "router", APIRouter())

import fakeredis.aioredis  # noqa: E402
import httpx  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from api.app import routes_alerts  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.utils import webhook_probe  # noqa: E402

app.state.redis = fakeredis.aioredis.FakeRedis()


def test_create_rule_probes_webhook(monkeypatch):
    called = {}

    async def fake_probe(url: str):
        called["url"] = url
        return {
            "tls": {"version": "TLSv1.3", "expires_at": None},
            "latency_ms": {"p50": 2000, "p95": 2000},
            "status_codes": [200, 200, 200],
            "allowed": True,
            "warnings": ["slow"],
        }

    monkeypatch.setattr(routes_alerts, "probe_webhook", fake_probe)

    class DummySession:
        def add(self, obj):
            obj.id = 1

        async def commit(self):
            pass

    @asynccontextmanager
    async def fake_session(tenant_id: str):
        yield DummySession()

    monkeypatch.setattr(routes_alerts, "_session", fake_session)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/outlet/t1/alerts/rules",
                json={
                    "event": "order.created",
                    "channel": "webhook",
                    "target": "https://example.com/hook",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "slow" in data["probe"]["warnings"]
    assert data["warning"] == "risky_webhook"
    assert called["url"] == "https://example.com/hook"


def test_probe_webhook_warns(monkeypatch):
    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def head(self, url):
            raise httpx.HTTPError("tls") from ssl.SSLCertVerificationError("bad cert")

    monkeypatch.setattr(webhook_probe.httpx, "AsyncClient", DummyClient)
    monkeypatch.setattr(webhook_probe, "is_allowed_url", lambda url: True)

    report = asyncio.run(webhook_probe.probe_webhook("https://bad"))
    assert set(report["warnings"]) == {"tls_self_signed", "bad_status"}
