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

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""
    # register sample for this request before generating output
    http_requests_total.labels(path="/metrics", method="GET", status="200").inc(0)
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)
