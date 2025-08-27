import json

import fakeredis.aioredis
from fastapi.testclient import TestClient

from api.app.main import app
import api.app.routes_status_json as routes_status_json


def test_status_route_serves_json(tmp_path, monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps({"state": "ok", "message": "", "components": []}))
    monkeypatch.setattr(routes_status_json, "STATUS_FILE", status_file)
    client = TestClient(app)
    resp = client.get("/status.json")
    assert resp.status_code == 200
    expected = json.loads(status_file.read_text())
    assert resp.json() == expected
    assert resp.headers["content-type"].startswith("application/json")
