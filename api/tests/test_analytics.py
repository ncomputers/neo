"""Analytics helper tests."""

from __future__ import annotations

import importlib
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import httpx

from api.app.services import analytics


async def _capture_post(self, url, json=None, data=None):  # type: ignore[override]
    _capture_post.calls.append({"url": url, "json": json, "data": data})
    class Resp:
        status_code = 200

    return Resp()


_capture_post.calls = []  # type: ignore[attr-defined]


def test_track_requires_consent(monkeypatch):
    monkeypatch.setenv("TENANT_ANALYTICS_ENABLED", "1")
    monkeypatch.setenv("POSTHOG_API_KEY", "phkey")
    monkeypatch.setenv("ANALYTICS_TENANTS", "")
    importlib.reload(analytics)
    monkeypatch.setattr(httpx.AsyncClient, "post", _capture_post, raising=False)

    import asyncio

    asyncio.run(analytics.track("demo", "evt", {"foo": "bar"}))
    assert _capture_post.calls == []  # no consent
def test_track_redacts_pii(monkeypatch):
    monkeypatch.setenv("TENANT_ANALYTICS_ENABLED", "1")
    monkeypatch.setenv("POSTHOG_API_KEY", "phkey")
    monkeypatch.setenv("ANALYTICS_TENANTS", "demo")
    importlib.reload(analytics)
    _capture_post.calls = []  # type: ignore[attr-defined]
    monkeypatch.setattr(httpx.AsyncClient, "post", _capture_post, raising=False)
    import asyncio

    asyncio.run(
        analytics.track(
            "demo",
            "evt",
            {"email": "a@b.com", "phone": "123", "name": "x", "foo": "bar"},
        )
    )
    assert _capture_post.calls
    props = _capture_post.calls[0]["json"]["batch"][0]["properties"]
    assert props == {"foo": "bar"}

