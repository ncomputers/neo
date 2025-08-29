import importlib.util
import pathlib
import sys


def test_owner_insights_email(monkeypatch):
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "owner_insights", root / "scripts/owner_insights.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["owner_insights"] = module
    spec.loader.exec_module(module)

    metrics = {
        "gross_sales": 1000.0,
        "orders": 50,
        "prep_p50": 10.0,
        "prep_p95": 20.0,
        "sla_hit_rate": 0.9,
        "top_items": [("Veg", 20)],
        "coupon_orders": 5,
    }
    monkeypatch.setattr(module, "fetch_metrics", lambda tenant, week_start: metrics)

    captured = {}

    def fake_send(event, payload, target):
        captured["payload"] = payload
        captured["target"] = target

    monkeypatch.setattr(module.email_stub, "send", fake_send)
    monkeypatch.setenv("OWNER_INSIGHTS_EMAIL", "owner@example.com")

    module.main("demo", "2024-01-01")
    attachments = captured["payload"]["attachments"]
    names = {name for name, *_ in attachments}
    assert {"weekly.csv", "weekly.pdf"}.issubset(names)
    assert captured["target"] == "owner@example.com"
