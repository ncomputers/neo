from pathlib import Path

import responses

from scripts.export_resume import stream


@responses.activate
def test_partial_resume(tmp_path: Path):
    url = "http://example.com/export"
    out = tmp_path / "out.csv"

    responses.add(
        responses.GET,
        url,
        body="part1",
        headers={"X-Cursor": "abc"},
    )
    responses.add(responses.GET, url, body="part2")

    stream(url, str(out), None)

    assert out.read_text() == "part1part2"
    # second request should include cursor
    assert responses.calls[1].request.url == f"{url}?cursor=abc"
