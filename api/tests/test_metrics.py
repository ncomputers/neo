import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app


def test_metrics_endpoint():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    assert "http_requests_total" in body
    assert "orders_created_total" in body
    assert "invoices_generated_total" in body
