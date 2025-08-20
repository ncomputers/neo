from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config import AcceptanceMode
from api.app.utils import (
    PrepTimeTracker,
    accepted_items,
    check_sla_breach,
    filter_out_of_stock_items,
)


def test_prep_time_tracker_ema():
    tracker = PrepTimeTracker(window=10)
    times = [10, 20, 30]
    ema = None
    for t in times:
        ema = tracker.add_prep_time(t)
    assert ema is not None
    # EMA should be between last value and average
    assert times[-1] >= ema >= min(times)


def test_accepted_items_modes():
    items = [
        {"id": 1, "accepted": True},
        {"id": 2, "accepted": False},
    ]
    assert accepted_items(items, AcceptanceMode.ITEM) == [items[0]]
    assert accepted_items(items, AcceptanceMode.ORDER) == []
    items[1]["accepted"] = True
    assert accepted_items(items, AcceptanceMode.ORDER) == items


def test_filter_out_of_stock_items():
    items = [
        {"id": 1, "in_stock": True},
        {"id": 2, "in_stock": False},
    ]
    assert filter_out_of_stock_items(items, hide=True) == [items[0]]
    assert filter_out_of_stock_items(items, hide=False) == items


def test_check_sla_breach():
    alerts = check_sla_breach(12, 10, sound_alert=True, color_alert=True)
    assert set(alerts) == {"sound", "color"}
    assert check_sla_breach(5, 10) == []


