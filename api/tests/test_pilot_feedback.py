import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_pilot_feedback import PILOT_FEEDBACK_STORE, router
from scripts import pilot_nps_digest

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def setup_module():
    PILOT_FEEDBACK_STORE.clear()


def test_submit_summary_and_digest():
    today = date.today().isoformat()
    assert (
        client.post(
            "/api/pilot/demo/feedback",
            json={"score": 10, "contact_opt_in": True},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/pilot/demo/feedback", json={"score": 7, "comment": "ok"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/pilot/demo/feedback", json={"score": 4, "comment": "meh"}
        ).status_code
        == 200
    )
    resp = client.get(f"/api/pilot/admin/feedback/summary?from={today}&to={today}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == {
        "promoters": 1,
        "passives": 1,
        "detractors": 1,
        "responses": 3,
    }

    summary = pilot_nps_digest.build_digest()
    assert "demo: nps=0.0 count=3" in summary
