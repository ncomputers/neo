# routes_metrics.py

"""Prometheus metrics and /metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest

# Counters
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["path", "method", "status"]
)
orders_created_total = Counter(
    "orders_created_total", "Total orders created"
)
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

http_errors_total = Counter(
    "http_errors_total", "Total HTTP errors", ["status"]
)
http_errors_total.labels(status="0").inc(0)

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""
    # register sample for this request before generating output
    http_requests_total.labels(path="/metrics", method="GET", status="200").inc(0)
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)
