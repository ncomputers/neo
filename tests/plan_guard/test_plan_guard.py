import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from scripts.plan_guard import compute_p95, guard_query  # noqa: E402


def test_compute_p95():
    assert compute_p95([1, 2, 3, 4, 5]) == 5


def test_guard_query_passes():
    durations = [5, 6, 7, 8, 9, 10]
    assert guard_query("ok", durations, 10) == 10


def test_guard_query_raises():
    durations = [5, 7, 9, 13, 14]
    with pytest.raises(RuntimeError):
        guard_query("slow", durations, 10)
