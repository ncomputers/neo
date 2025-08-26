from api.app.routes_exports import _cap_limit


def test_cap_limit():
    limit, capped = _cap_limit(200000)
    assert limit == 100000
    assert capped
