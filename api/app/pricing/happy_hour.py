"""Helpers for time-based discount pricing."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Mapping, Sequence


DAY_MAP = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def _to_time(value: str) -> time:
    """Convert ``HH:MM`` strings to :class:`~datetime.time` objects."""

    return datetime.strptime(value, "%H:%M").time()


def active_windows(
    windows: Sequence[Mapping[str, object]] | None,
    now: datetime | time | None = None,
) -> list[Mapping[str, object]]:
    """Return active discount windows for ``now``.

    Parameters
    ----------
    windows:
        Sequence of window mappings with optional ``days`` list containing
        weekday abbreviations (``mon``-``sun``) or indices (0=Mon).
    now:
        Reference time. Defaults to :func:`datetime.now`.
    """

    if not windows:
        return []

    dt = now or datetime.now()
    if isinstance(dt, time):
        dt = datetime.combine(datetime.today(), dt)
    weekday = dt.weekday()
    current_time = dt.time()
    active: list[Mapping[str, object]] = []
    for win in windows:
        days = win.get("days")
        if days:
            day_indexes: set[int] = set()
            for d in days:  # type: ignore[assignment]
                if isinstance(d, int):
                    day_indexes.add(d)
                else:
                    day_indexes.add(DAY_MAP[str(d).lower()[:3]])
            if weekday not in day_indexes:
                continue
        start = _to_time(str(win["start"]))
        end = _to_time(str(win["end"]))
        if start <= current_time < end:
            active.append(win)
    return active


def apply_discount(
    price: Decimal, windows: Sequence[Mapping[str, object]] | None
) -> Decimal:
    """Return ``price`` adjusted per the best matching ``windows`` discount."""

    if not windows:
        return price
    best = price
    for win in windows:
        candidate = price
        if "percent" in win:
            pct = Decimal(str(win["percent"]))
            candidate = price * (Decimal("100") - pct) / Decimal("100")
        elif "flat" in win:
            candidate = price - Decimal(str(win["flat"]))
        candidate = max(candidate, Decimal("0"))
        if candidate < best:
            best = candidate
    return best
