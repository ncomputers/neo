import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.app.routes_rum_vitals as routes_rum_vitals
from api.app.routes_rum_vitals import cls_hist, inp_hist, lcp_hist, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _metric_sum(hist, route: str = "/admin") -> float:
    return hist.labels(route=route)._sum.get()


def test_requires_flag_and_consent(monkeypatch):
    before = _metric_sum(lcp_hist)

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: False)
    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": True, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(lcp_hist, "/admin") == before

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: True)
    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": False, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(lcp_hist, "/admin") == before

    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": True, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(lcp_hist, "/admin") == before + 1.2
    assert _metric_sum(lcp_hist, "/other") == 0


def test_cls_requires_flag_and_consent(monkeypatch):
    before = _metric_sum(cls_hist)

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: False)
    client.post(
        "/rum/vitals",
        json={"cls": 0.5, "consent": True, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(cls_hist, "/admin") == before

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: True)
    client.post(
        "/rum/vitals",
        json={"cls": 0.5, "consent": False, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(cls_hist, "/admin") == before

    client.post(
        "/rum/vitals",
        json={"cls": 0.5, "consent": True, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(cls_hist, "/admin") == before + 0.5
    assert _metric_sum(cls_hist, "/other") == 0


def test_inp_requires_flag_and_consent(monkeypatch):
    before = _metric_sum(inp_hist)

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: False)
    client.post(
        "/rum/vitals",
        json={"inp": 1.0, "consent": True, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(inp_hist, "/admin") == before

    monkeypatch.setattr(routes_rum_vitals, "get_flag", lambda name, tenant=None: True)
    client.post(
        "/rum/vitals",
        json={"inp": 1.0, "consent": False, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(inp_hist, "/admin") == before

    client.post(
        "/rum/vitals",
        json={"inp": 1.0, "consent": True, "route": "/admin"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum(inp_hist, "/admin") == before + 1.0
    assert _metric_sum(inp_hist, "/other") == 0
