import asyncio
import pathlib
import sys
from unittest import mock

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.app.pdf.render import render_template  # noqa: E402
from api.app.routes_onboarding import TENANTS  # noqa: E402
from api.app.routes_onboarding import router as onboarding_router  # noqa: E402
from api.app.routes_qrpack import router as qrpack_router  # noqa: E402


def _setup_app():
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.include_router(onboarding_router)
    app.include_router(qrpack_router)
    return app


def test_onboarding_persists_all_fields():
    app = _setup_app()
    client = TestClient(app)

    start = client.post("/api/onboarding/start").json()["data"]
    oid = start["onboarding_id"]

    profile = {
        "name": "Cafe Neo",
        "address": "1, Example St",
        "logo_url": "http://logo/neo.png",
        "timezone": "UTC",
        "language": "en",
    }
    assert (
        client.post(f"/api/onboarding/{oid}/profile", json=profile).status_code == 200
    )

    tax = {"mode": "regular", "gstin": "GST123", "hsn_required": True}
    assert client.post(f"/api/onboarding/{oid}/tax", json=tax).status_code == 200

    tables = {"count": 2}
    table_resp = client.post(f"/api/onboarding/{oid}/tables", json=tables).json()[
        "data"
    ]
    assert len(table_resp) == 2

    payments = {
        "vpa": "neo@upi",
        "central_vpa": True,
        "modes": {"cash": True, "upi": True, "card": False},
    }
    assert (
        client.post(f"/api/onboarding/{oid}/payments", json=payments).status_code == 200
    )

    finish = client.post(f"/api/onboarding/{oid}/finish").json()["data"]
    tid = finish["tenant_id"]

    tenant = TENANTS[tid]
    assert tenant["profile"]["name"] == "Cafe Neo"
    assert tenant["tax"]["mode"] == "regular"
    assert len(tenant["tables"]) == 2
    assert tenant["payments"]["modes"]["upi"] is True


def test_qrpack_pdf_includes_all_codes():
    app = _setup_app()
    client = TestClient(app)

    oid = client.post("/api/onboarding/start").json()["data"]["onboarding_id"]
    client.post(
        f"/api/onboarding/{oid}/profile",
        json={
            "name": "Cafe",
            "address": "1 St",
            "logo_url": "",
            "timezone": "UTC",
            "language": "en",
        },
    )
    client.post(f"/api/onboarding/{oid}/tables", json={"count": 3})
    client.post(f"/api/onboarding/{oid}/finish")

    resp = client.get(f"/api/outlet/{oid}/qrpack.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf") or resp.headers[
        "content-type"
    ].startswith("text/html")
    content = resp.content
    for label in [b"Table 1", b"Table 2", b"Table 3"]:
        assert label in content


def test_per_page_affects_page_count_and_label_fmt():
    app = _setup_app()
    client = TestClient(app)

    def onboard(count: int) -> str:
        oid = client.post("/api/onboarding/start").json()["data"]["onboarding_id"]
        client.post(
            f"/api/onboarding/{oid}/profile",
            json={
                "name": "Cafe",
                "address": "1 St",
                "logo_url": "",
                "timezone": "UTC",
                "language": "en",
            },
        )
        client.post(f"/api/onboarding/{oid}/tables", json={"count": count})
        client.post(f"/api/onboarding/{oid}/finish")
        return oid

    oid_small = onboard(30)
    resp_small = client.get(
        f"/api/outlet/{oid_small}/qrpack.pdf?per_page=6&label_fmt=Desk%20{{n}}"
    )

    oid_large = onboard(30)
    resp_large = client.get(
        f"/api/outlet/{oid_large}/qrpack.pdf?per_page=24&label_fmt=Desk%20{{n}}"
    )

    assert resp_small.status_code == 200 and resp_large.status_code == 200

    count_small = resp_small.content.count(b"<table")
    count_large = resp_large.content.count(b"<table")
    assert count_small > count_large
    assert b"Desk 1" in resp_small.content


def test_size_and_logo_options_applied():
    app = _setup_app()
    client = TestClient(app)

    def onboard() -> str:
        oid = client.post("/api/onboarding/start").json()["data"]["onboarding_id"]
        client.post(
            f"/api/onboarding/{oid}/profile",
            json={
                "name": "Cafe",
                "address": "1 St",
                "logo_url": "http://logo.png",
                "timezone": "UTC",
                "language": "en",
            },
        )
        client.post(f"/api/onboarding/{oid}/tables", json={"count": 1})
        client.post(f"/api/onboarding/{oid}/finish")
        return oid

    oid_logo = onboard()
    resp_logo = client.get(f"/api/outlet/{oid_logo}/qrpack.pdf?size=Letter")
    assert b"size: Letter" in resp_logo.content
    assert b"http://logo.png" in resp_logo.content

    oid_no_logo = onboard()
    resp_no_logo = client.get(
        f"/api/outlet/{oid_no_logo}/qrpack.pdf?size=A3&show_logo=false"
    )
    assert b"size: A3" in resp_no_logo.content
    assert b"http://logo.png" not in resp_no_logo.content


def test_qrpack_cache_hit():
    app = _setup_app()
    client = TestClient(app)

    oid = client.post("/api/onboarding/start").json()["data"]["onboarding_id"]
    client.post(
        f"/api/onboarding/{oid}/profile",
        json={
            "name": "Cafe",
            "address": "1",
            "logo_url": "",
            "timezone": "UTC",
            "language": "en",
        },
    )
    client.post(f"/api/onboarding/{oid}/tables", json={"count": 1})
    client.post(f"/api/onboarding/{oid}/finish")

    with mock.patch(
        "api.app.routes_qrpack.render_template", wraps=render_template
    ) as rtpl:
        resp1 = client.get(f"/api/outlet/{oid}/qrpack.pdf")
        assert resp1.status_code == 200
        assert rtpl.call_count == 1

        asyncio.run(app.state.redis.delete(f"qrpack:rl:{oid}"))

        rtpl.reset_mock()
        resp2 = client.get(f"/api/outlet/{oid}/qrpack.pdf")
        assert resp2.status_code == 200
        rtpl.assert_not_called()


def test_qrpack_rate_limiter():
    app = _setup_app()
    client = TestClient(app)

    oid = client.post("/api/onboarding/start").json()["data"]["onboarding_id"]
    client.post(
        f"/api/onboarding/{oid}/profile",
        json={
            "name": "Cafe",
            "address": "1",
            "logo_url": "",
            "timezone": "UTC",
            "language": "en",
        },
    )
    client.post(f"/api/onboarding/{oid}/tables", json={"count": 1})
    client.post(f"/api/onboarding/{oid}/finish")

    assert client.get(f"/api/outlet/{oid}/qrpack.pdf").status_code == 200
    assert client.get(f"/api/outlet/{oid}/qrpack.pdf").status_code == 429
