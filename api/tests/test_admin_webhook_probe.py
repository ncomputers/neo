import asyncio
import pathlib
import sys
import types
import os

from httpx import ASGITransport, AsyncClient
import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

sys.modules.setdefault("PIL", types.ModuleType("PIL"))
sys.modules.setdefault("PIL.Image", types.ModuleType("Image"))
sys.modules.setdefault("PIL.ImageOps", types.ModuleType("ImageOps"))

from api.app.main import app  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app import routes_admin_webhooks  # noqa: E402

app.state.redis = fakeredis.aioredis.FakeRedis()


def test_probe_endpoint_stores_report(monkeypatch):
    report = {
        "tls": {"version": "TLSv1.3", "expires_at": None},
        "latency_ms": {"p50": 10, "p95": 20},
        "status_codes": [200, 200, 200],
        "allowed": True,
        "warnings": [],
    }

    async def fake_probe(url: str):
        return report

    monkeypatch.setattr(routes_admin_webhooks, "probe_webhook", fake_probe)

    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})

    async def _run():
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/admin/webhooks/probe",
                json={"url": "https://example.com/hook"},
                headers={"Authorization": f"Bearer {token}"},
            )
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    assert resp.json()["data"] == report
    assert (
        routes_admin_webhooks.PROBE_REPORTS["https://example.com/hook"]
        == report
    )
