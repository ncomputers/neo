from __future__ import annotations

from typing import Iterable

from config import AcceptanceMode


class PrepTimeTracker:
    """Track preparation times using an exponential moving average."""

    def __init__(self, window: int) -> None:
        if window not in {10, 20}:
            msg = "window must be 10 or 20"
            raise ValueError(msg)
        self.window = window
        self._ema: float | None = None

    @property
    def ema(self) -> float | None:
        return self._ema

    def add_prep_time(self, prep_time: float) -> float:
        alpha = 2 / (self.window + 1)
        self._ema = (
            prep_time
            if self._ema is None
            else alpha * prep_time + (1 - alpha) * self._ema
        )
        return self._ema


def accepted_items(items: Iterable[dict], mode: AcceptanceMode) -> list[dict]:
    """Return accepted items based on the provided mode."""

    item_list = list(items)
    if mode is AcceptanceMode.ORDER:
        accepted = all(item.get("accepted", False) for item in item_list)
        return item_list if accepted else []
    return [item for item in item_list if item.get("accepted", False)]


def filter_out_of_stock_items(items: Iterable[dict], hide: bool) -> list[dict]:
    """Optionally remove out-of-stock items from the provided iterable."""

    if not hide:
        return list(items)
    return [item for item in items if item.get("in_stock", True)]


def check_sla_breach(
    prep_time: float,
    sla_seconds: float,
    *,
    sound_alert: bool = False,
    color_alert: bool = False,
) -> list[str]:
    """Return triggered alerts if the SLA is breached."""

    if prep_time <= sla_seconds:
        return []
    alerts: list[str] = []
    if sound_alert:
        alerts.append("sound")
    if color_alert:
        alerts.append("color")
    return alerts
