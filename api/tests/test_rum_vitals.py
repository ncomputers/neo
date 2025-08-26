import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.app.routes_rum_vitals as routes_rum_vitals
from api.app.routes_rum_vitals import router, lcp_hist

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _metric_sum(route: str = "/home") -> float:
    return lcp_hist.labels(route=route)._sum.get()


def test_requires_flag_and_consent(monkeypatch):
    before = _metric_sum()

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: False)
    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": True, "route": "/home"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum("/home") == before

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: True)
    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": False, "route": "/home"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum("/home") == before

    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": True, "route": "/home"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum("/home") == before + 1.2
    assert _metric_sum("/other") == 0
