import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

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
    assert "notifications_outbox_delivered_total" in body
    assert "notifications_outbox_failed_total" in body
    assert "sse_clients_gauge" in body
    assert "ws_messages_total" in body
    assert "digest_sent_total" in body
    assert "db_replica_healthy" in body
