# routes_metrics.py

"""Prometheus metrics and /metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from datetime import datetime, timezone

# Counters
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["path", "method", "status"]
)
orders_created_total = Counter("orders_created_total", "Total orders created")
orders_created_total.inc(0)

invoices_generated_total = Counter(
    "invoices_generated_total", "Total invoices generated"
)
invoices_generated_total.inc(0)

idempotency_hits_total = Counter(
    "idempotency_hits_total", "Total requests with an idempotency key present"
)
idempotency_hits_total.inc(0)

idempotency_conflicts_total = Counter(
    "idempotency_conflicts_total", "Total idempotency key conflicts"
)
idempotency_conflicts_total.inc(0)

table_locked_denied_total = Counter(
    "table_locked_denied_total", "Total requests denied due to locked tables"
)
table_locked_denied_total.inc(0)

room_locked_denied_total = Counter(
    "room_locked_denied_total", "Total requests denied due to locked rooms"
)
room_locked_denied_total.inc(0)

http_errors_total = Counter("http_errors_total", "Total HTTP errors", ["status"])
http_errors_total.labels(status="0").inc(0)

slo_requests_total = Counter(
    "slo_requests_total", "Total requests for SLO tracking", ["route"]
)
slo_requests_total.labels(route="/sample").inc(0)

slo_errors_total = Counter(
    "slo_errors_total", "Total error requests for SLO tracking", ["route"]
)
slo_errors_total.labels(route="/sample").inc(0)


notifications_outbox_delivered_total = Counter(
    "notifications_outbox_delivered_total",
    "Total notifications delivered from outbox",
)
notifications_outbox_delivered_total.inc(0)

notifications_outbox_failed_total = Counter(
    "notifications_outbox_failed_total",
    "Total notifications that failed from outbox",
)
notifications_outbox_failed_total.inc(0)

webhook_attempts_total = Counter(
    "webhook_attempts_total", "Total webhook delivery attempts", ["destination"]
)
webhook_attempts_total.labels(destination="sample").inc(0)

webhook_failures_total = Counter(
    "webhook_failures_total", "Total webhook delivery failures", ["destination"]
)
webhook_failures_total.labels(destination="sample").inc(0)

webhook_breaker_state = Gauge(
    "webhook_breaker_state",
    "Circuit breaker state for webhook destinations (0 closed, 1 open, 2 half-open)",
    ["url_hash"],
)
webhook_breaker_state.labels(url_hash="sample").set(0)

db_replica_healthy = Gauge(
    "db_replica_healthy", "Replica database health (1 healthy, 0 unhealthy)"
)
db_replica_healthy.set(0)

sse_clients_gauge = Gauge(
    "sse_clients_gauge", "Current number of connected SSE clients"
)
sse_clients_gauge.set(0)

ws_messages_total = Counter("ws_messages_total", "Total WebSocket messages sent")
ws_messages_total.inc(0)

digest_sent_total = Counter("digest_sent_total", "Total digests sent")
digest_sent_total.inc(0)

rollup_runs_total = Counter("rollup_runs_total", "Total rollup runs")
rollup_runs_total.inc(0)

rollup_failures_total = Counter("rollup_failures_total", "Total rollup failures")
rollup_failures_total.inc(0)

printer_retry_queue = Gauge("printer_retry_queue", "Queued print jobs awaiting retry")
printer_retry_queue.set(0)
printer_retry_queue_age = Gauge(
    "printer_retry_queue_age",
    "Age in seconds of the oldest job awaiting retry",
)
printer_retry_queue_age.set(0)

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics."""
    http_requests_total.labels(path="/metrics", method="GET", status="200").inc(0)
    redis = getattr(request.app.state, "redis", None)
    if redis:
        total = 0
        max_age = 0
        now = datetime.now(timezone.utc)
        for key in await redis.keys("print:retry:*"):
            length = await redis.llen(key)
            total += length
            head = await redis.lindex(key, 0)
            if head:
                if isinstance(head, bytes):
                    head = head.decode()
                try:
                    ts = datetime.fromisoformat(head)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    age = (now - ts).total_seconds()
                    if age > max_age:
                        max_age = age
                except ValueError:
                    pass
        printer_retry_queue.set(total)
        printer_retry_queue_age.set(max_age)
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)
