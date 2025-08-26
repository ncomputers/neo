import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.exp import ab_allocator


def test_allocation_is_stable():
    variants = {"control": 1, "treat": 1}
    did = "device-123"
    first = ab_allocator.allocate(did, "exp", variants)
    second = ab_allocator.allocate(did, "exp", variants)
    assert first == second


def test_weighted_distribution():
    variants = {"control": 1, "treat": 3}
    counts = {"control": 0, "treat": 0}
    for i in range(1000):
        v = ab_allocator.allocate(f"id-{i}", "exp", variants)
        counts[v] += 1
    ratio = counts["treat"] / counts["control"]
    assert 2.0 < ratio < 4.0
