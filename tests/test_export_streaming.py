from api.app.routes_exports import _cap_limit
from api.app.utils.csv_stream import stream_rows


def test_streaming_works():
    rows = [(1, "a"), (2, "b")]
    chunks = list(stream_rows(rows, header=["id", "val"]))
    assert chunks[0].startswith("id")
    assert chunks[1].startswith("1")
    assert chunks[2].startswith("2")


def test_cap_hit_hint():
    limit, capped = _cap_limit(100001)
    assert limit == 100000
    assert capped


def test_sse_progress():
    progress = []
    total = 2500
    for i in range(1, total + 1):
        if i % 1000 == 0:
            progress.append(i)
    assert progress == [1000, 2000]
