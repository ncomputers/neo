import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_pilot_feedback import router, PILOT_FEEDBACK_STORE
from scripts import pilot_nps_digest

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def setup_module():
    PILOT_FEEDBACK_STORE.clear()


def test_submit_and_digest():
    assert client.post(
        "/api/pilot/demo/feedback", json={"score": 10}
    ).status_code == 200
    assert (
        client.post(
            "/api/pilot/demo/feedback", json={"score": 9, "comment": "great"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/pilot/demo/feedback", json={"score": 4, "comment": "meh"}
        ).status_code
        == 200
    )
    summary = pilot_nps_digest.build_digest()
    assert "demo: nps=33.3 count=3" in summary
