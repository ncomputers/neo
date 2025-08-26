from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.middlewares.prometheus import PrometheusMiddleware
from api.app.routes_metrics import router as metrics_router


class DummyRedis:
    async def sismember(self, *args, **kwargs):
        return False

    async def incr(self, *args, **kwargs):
        return 0

    async def sadd(self, *args, **kwargs):
        return 0

    async def keys(self, *args, **kwargs):
        return []

    async def llen(self, *args, **kwargs):
        return 0


def test_metrics_expose_counters():
    app = FastAPI()
    app.add_middleware(PrometheusMiddleware)
    app.include_router(metrics_router)
    app.state.redis = DummyRedis()
    client = TestClient(app)
    client.get("/missing")
    resp = client.get("/metrics")
    text = resp.text
    assert "idempotency_hits_total" in text
    assert "idempotency_conflicts_total" in text
    assert "table_locked_denied_total" in text
    assert "room_locked_denied_total" in text
    assert "http_requests_total" in text
    assert 'status="404"' in text
    assert "notifications_outbox_delivered_total" in text
    assert "notifications_outbox_failed_total" in text
    assert "sse_clients_gauge" in text
    assert "ws_messages_total" in text
    assert "digest_sent_total" in text
    assert "printer_retry_queue" in text
