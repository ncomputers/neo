"""Helpers for time-based discount pricing."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Mapping, Sequence


def _to_time(value: str) -> time:
    """Convert ``HH:MM`` strings to :class:`~datetime.time` objects."""

    return datetime.strptime(value, "%H:%M").time()


def active_window(
    windows: Sequence[Mapping[str, object]] | None, now: time | None = None
):
    """Return the active discount window for ``now`` if any."""

    if not windows:
        return None
    now = now or datetime.now().time()
    for win in windows:
        start = _to_time(str(win["start"]))
        end = _to_time(str(win["end"]))
        if start <= now < end:
            return win
    return None


def apply_discount(price: Decimal, window: Mapping[str, object] | None) -> Decimal:
    """Return ``price`` adjusted per ``window`` discount."""

    if not window:
        return price
    if "percent" in window:
        pct = Decimal(str(window["percent"]))
        price = price * (Decimal("100") - pct) / Decimal("100")
    elif "flat" in window:
        price = price - Decimal(str(window["flat"]))
    return max(price, Decimal("0"))
