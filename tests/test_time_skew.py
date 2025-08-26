from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.app.main import app


def test_time_skew_endpoint():
    client = TestClient(app)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    resp = client.get("/time/skew", params={"client_ts": now_ms})
    assert resp.status_code == 200
    data = resp.json()
    assert "server_time" in data
    assert "advice" in data
    assert "skew_ms" in data
