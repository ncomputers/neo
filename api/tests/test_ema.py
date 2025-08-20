from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from api.app.services.ema import eta, update_ema


def test_update_ema_first_sample():
    assert update_ema(None, 10, 10) == 10


def test_update_ema_subsequent_sample():
    prev = 10
    sample = 20
    n = 10
    alpha = 2 / (n + 1)
    expected = alpha * sample + (1 - alpha) * prev
    assert update_ema(prev, sample, n) == expected


def test_eta_with_items():
    current = [10, 20]
    assert eta(current, 15) == 45


def test_eta_empty_queue():
    assert eta([], 12) == 12
