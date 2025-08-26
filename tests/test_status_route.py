import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.app.main import app


def test_status_route_serves_json():
    client = TestClient(app)
    resp = client.get("/status.json")
    assert resp.status_code == 200
    status_path = Path(__file__).resolve().parent.parent / "status.json"
    with status_path.open() as f:
        expected = json.load(f)
    assert resp.json() == expected
    assert resp.headers["content-type"].startswith("application/json")
