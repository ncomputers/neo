"""Pilot telemetry endpoints for ops dashboard."""

from __future__ import annotations

import statistics
import time
from collections import deque
from typing import Any, Deque, Tuple

from fastapi import APIRouter, Request

from .middlewares.logging import latency_samples
from .routes_metrics import (
    http_errors_total,
    http_requests_total,
    kds_oldest_kot_seconds,
    orders_created_total,
    sse_clients_gauge,
    webhook_breaker_state,
)
from .utils.responses import ok

router = APIRouter()

_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_LAST_ORDERS_TOTAL: float | None = None
_LAST_ORDERS_TS: float | None = None
_ERROR_HISTORY: Deque[Tuple[float, float, float]] = deque()
_CACHE_TTL = 60
_ERR_WINDOW = 300  # 5 minutes


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


def _avg_prep_s() -> float:
    """Average prep time from in-memory trackers."""
    from . import main as main_mod  # local import to avoid circular

    emas = [t.ema for t in main_mod.prep_trackers.values() if t.ema is not None]
    return float(statistics.mean(emas)) if emas else 0.0


def _webhook_breaker_open_pct() -> float:
    metrics = webhook_breaker_state._metrics.values()
    total = len(metrics)
    if not total:
        return 0.0
    opened = sum(1 for m in metrics if m._value.get() == 1)
    return (opened / total) * 100.0


def _kot_queue_oldest_s() -> float:
    metrics = kds_oldest_kot_seconds._metrics.values()
    return max((m._value.get() for m in metrics), default=0.0)


def _p95_latency_ms() -> float:
    samples = list(latency_samples)
    if not samples:
        return 0.0
    samples.sort()
    idx = max(int(len(samples) * 0.95) - 1, 0)
    return float(samples[idx])


def _error_rate_5m(now: float) -> float:
    req_total = sum(m._value.get() for m in http_requests_total._metrics.values())
    err_total = sum(m._value.get() for m in http_errors_total._metrics.values())
    _ERROR_HISTORY.append((now, req_total, err_total))
    while _ERROR_HISTORY and _ERROR_HISTORY[0][0] < now - _ERR_WINDOW:
        _ERROR_HISTORY.popleft()
    first_ts, first_req, first_err = _ERROR_HISTORY[0]
    delta_req = req_total - first_req
    delta_err = err_total - first_err
    return delta_err / delta_req if delta_req else 0.0


def _sse_clients() -> float:
    return sse_clients_gauge._value.get()


@router.get("/api/admin/pilot/telemetry")
async def pilot_telemetry(_request: Request) -> dict[str, Any]:
    """Return real-time pilot telemetry with 60s cache."""
    now = time.time()
    cached = _CACHE.get("data")
    if cached and now - _CACHE["ts"] < _CACHE_TTL:
        return ok(cached)

    data = {
        "orders_per_min": _orders_per_min(now),
        "avg_prep_s": _avg_prep_s(),
        "kot_queue_oldest_s": _kot_queue_oldest_s(),
        "p95_latency_ms": _p95_latency_ms(),
        "error_rate_5m": _error_rate_5m(now),
        "webhook_breaker_open_pct": _webhook_breaker_open_pct(),
        "sse_clients": _sse_clients(),
        "timestamp": int(now),
    }
    _CACHE["ts"] = now
    _CACHE["data"] = data
    return ok(data)
