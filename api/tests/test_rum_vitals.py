import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.app.routes_rum as routes_rum
from api.app.routes_rum import router, lcp_hist

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _metric_sum() -> float:
    return lcp_hist.labels(ctx="guest")._sum.get()


def test_requires_flag_and_consent(monkeypatch):
    before = _metric_sum()

    monkeypatch.setattr(routes_rum, "get_flag", lambda name, tenant=None: False)
    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": True},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum() == before

    monkeypatch.setattr(routes_rum, "get_flag", lambda name, tenant=None: True)
    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": False},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum() == before

    client.post(
        "/rum/vitals",
        json={"lcp": 1.2, "consent": True},
        headers={"X-Tenant-ID": "demo"},
    )
    assert _metric_sum() == before + 1.2
