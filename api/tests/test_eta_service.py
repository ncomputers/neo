import datetime

from api.app.eta import service


class _Cfg:
    prep_sla_min = 10
    eta_confidence = "p50"
    max_queue_factor = 1.6


def _fake_settings():
    return _Cfg


def test_queue_cap(monkeypatch):
    monkeypatch.setattr(service, "get_settings", _fake_settings)
    items = [{"item_id": "a", "p50_s": 60}, {"item_id": "b", "p50_s": 80}]
    result = service.eta_for_order(
        items, active_tickets=10, now=datetime.datetime(2023, 1, 1)
    )
    assert result["eta_ms"] == int(80 * 1.6 * 1000)
    assert result["components"][0]["factor"] == 1.6


def test_confidence(monkeypatch):
    class Cfg:
        prep_sla_min = 10
        eta_confidence = "p80"
        max_queue_factor = 1.6

    monkeypatch.setattr(service, "get_settings", lambda: Cfg)
    items = [{"item_id": "a", "p80_s": 120}]
    result = service.eta_for_order(
        items, active_tickets=1, now=datetime.datetime(2023, 1, 1)
    )
    assert result["eta_ms"] == 120 * 1000
