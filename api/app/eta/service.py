from __future__ import annotations

"""Helpers to estimate order preparation times."""

from datetime import datetime, timedelta
from typing import Dict, List

from config import get_settings


def _queue_factor(active_tickets: int, max_factor: float) -> float:
    """Return queue multiplier capped by ``max_factor``."""
    if active_tickets <= 1:
        return 1.0
    factor = 1 + (max_factor - 1) * (active_tickets - 1)
    return min(factor, max_factor)


def eta_for_order(
    items: List[Dict[str, float]],
    active_tickets: int,
    now: datetime | None = None,
) -> Dict[str, object]:
    """Estimate ETA for an order given its ``items``.

    Each item dict may contain percentile keys such as ``p50_s`` or ``p80_s``.
    ``active_tickets`` represents the number of outstanding tickets including
    the current order.
    """
    settings = get_settings()
    conf_key = f"{settings.eta_confidence}_s"
    default = settings.prep_sla_min * 60
    q_factor = _queue_factor(active_tickets, settings.max_queue_factor)
    bases = [item.get(conf_key, default) for item in items]
    base_max = max(bases) if bases else default
    eta_s = base_max * q_factor
    now = now or datetime.utcnow()
    promised_at = now + timedelta(seconds=eta_s)
    components = [
        {
            "item_id": item.get("item_id"),
            "base_s": item.get(conf_key, default),
            "factor": q_factor,
        }
        for item in items
    ]
    return {
        "eta_ms": int(eta_s * 1000),
        "promised_at": promised_at,
        "components": components,
    }
