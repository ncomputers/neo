"""Service layer helpers for the API."""

from .ema import eta, update_ema

try:  # pragma: no cover - optional until KDS models stabilise
    from .kds_service import accept_order, bump_item, queue_view
except Exception:  # pragma: no cover - fallback when dependencies missing
    accept_order = bump_item = queue_view = None

__all__ = [
    "eta",
    "update_ema",
    "accept_order",
    "bump_item",
    "queue_view",
]
