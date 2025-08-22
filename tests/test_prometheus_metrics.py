import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.app.main import app


class DummyRedis:
    async def sismember(self, *args, **kwargs):
        return False

    async def incr(self, *args, **kwargs):
        return 0

    async def sadd(self, *args, **kwargs):
        return 0


def test_metrics_expose_counters():
    app.state.redis = DummyRedis()
    client = TestClient(app)
    client.get("/missing")
    resp = client.get("/metrics")
    text = resp.text
    assert "idempotency_hits_total" in text
    assert "idempotency_conflicts_total" in text
    assert "table_locked_denied_total" in text
    assert "room_locked_denied_total" in text
    assert "http_errors_total" in text
    assert 'http_errors_total{status="404"}' in text
