"""Pilot telemetry endpoints."""

from __future__ import annotations

import statistics
import time
from typing import Any

from fastapi import APIRouter, Request

from .middlewares.logging import latency_samples
from .routes_metrics import (
    http_errors_total,
    http_requests_total,
    kds_oldest_kot_seconds,
    orders_created_total,
    webhook_breaker_state,
)
from .utils.responses import ok

router = APIRouter()

_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_LAST_ORDERS_TOTAL: float | None = None
_LAST_ORDERS_TS: float | None = None
_CACHE_TTL = 60


def _orders_per_min(now: float) -> float:
    """Compute orders per minute based on counter delta."""
    global _LAST_ORDERS_TOTAL, _LAST_ORDERS_TS
    total = orders_created_total._value.get()
    if _LAST_ORDERS_TOTAL is None or _LAST_ORDERS_TS is None:
        rate = 0.0
    else:
        diff = total - _LAST_ORDERS_TOTAL
        elapsed = now - _LAST_ORDERS_TS
        rate = diff / (elapsed / 60) if elapsed > 0 else 0.0
    _LAST_ORDERS_TOTAL = total
    _LAST_ORDERS_TS = now
    return rate


def _avg_prep() -> float:
    """Average prep time from in-memory trackers."""
    from . import main as main_mod  # local import to avoid circular

    emas = [t.ema for t in main_mod.prep_trackers.values() if t.ema is not None]
    return float(statistics.mean(emas)) if emas else 0.0


def _breaker_open_pct() -> float:
    metrics = webhook_breaker_state._metrics.values()
    total = len(metrics)
    if not total:
        return 0.0
    opened = sum(1 for m in metrics if m._value.get() == 1)
    return (opened / total) * 100.0


def _kot_queue_age() -> float:
    metrics = kds_oldest_kot_seconds._metrics.values()
    return max((m._value.get() for m in metrics), default=0.0)


def _latency_p95() -> float:
    samples = list(latency_samples)
    if not samples:
        return 0.0
    samples.sort()
    idx = max(int(len(samples) * 0.95) - 1, 0)
    return float(samples[idx])


def _error_rate() -> float:
    total = sum(m._value.get() for m in http_requests_total._metrics.values())
    errors = sum(m._value.get() for m in http_errors_total._metrics.values())
    return errors / total if total else 0.0


@router.get("/api/admin/pilot/telemetry")
async def pilot_telemetry(_request: Request) -> dict[str, Any]:
    """Return real-time pilot telemetry with 60s cache."""
    now = time.time()
    cached = _CACHE.get("data")
    if cached and now - _CACHE["ts"] < _CACHE_TTL:
        return ok(cached)

    data = {
        "orders_per_min": _orders_per_min(now),
        "avg_prep": _avg_prep(),
        "breaker_open_pct": _breaker_open_pct(),
        "kot_queue_age": _kot_queue_age(),
        "latency_p95_ms": _latency_p95(),
        "error_rate": _error_rate(),
    }
    _CACHE["ts"] = now
    _CACHE["data"] = data
    return ok(data)
