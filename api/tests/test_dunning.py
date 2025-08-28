import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts import dunning_scheduler as ds


def test_cadence_math_and_idempotency(tmp_path, monkeypatch):
    today = date(2023, 1, 1)
    tenants = [
        ds.Tenant(id="a", expires_at=today + timedelta(days=7)),
        ds.Tenant(id="b", expires_at=today + timedelta(days=3)),
        ds.Tenant(id="c", expires_at=today + timedelta(days=1)),
        ds.Tenant(id="d", expires_at=today),
        ds.Tenant(id="e", expires_at=today - timedelta(days=3)),
        ds.Tenant(id="f", expires_at=today - timedelta(days=7)),
        ds.Tenant(id="g", expires_at=today + timedelta(days=7), auto_renew=True),
        ds.Tenant(id="h", expires_at=today + timedelta(days=7), status="CANCELLED"),
    ]
    monkeypatch.setattr(ds, "EVENT_LOG", tmp_path / "log.json")
    scheduler = ds.DunningScheduler(today)
    count = scheduler.run(tenants)
    assert count == 6
    keys = [e["template_key"] for e in scheduler.events]
    assert keys == ["T-7", "T-3", "T-1", "T+0", "T+3", "T+7"]
    # idempotent
    scheduler2 = ds.DunningScheduler(today)
    monkeypatch.setattr(ds, "EVENT_LOG", tmp_path / "log.json")
    scheduler2.events = scheduler.events
    assert scheduler2.run(tenants) == 0


def test_snooze_suppresses_banner():
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse
    from fastapi.testclient import TestClient
    from jinja2 import Environment, FileSystemLoader

    from api.app.routes_admin_billing import router as billing_router

    app = FastAPI()
    app.include_router(billing_router)
    env = Environment(loader=FileSystemLoader("templates"))

    @app.get("/page")
    async def page(request: Request):
        request.state.license_status = "GRACE"
        request.state.license_days_left = 3
        template = env.get_template("base_admin.html")
        return HTMLResponse(template.render(request=request))

    client = TestClient(app)
    assert "Snooze for today" in client.get("/page").text
    cookies = client.post("/admin/billing/dunning/snooze").cookies
    assert "Snooze for today" not in client.get("/page", cookies=cookies).text


def test_channel_opt_out():
    settings = SimpleNamespace(dunning_email_enabled=True, dunning_wa_enabled=True)
    tenant = ds.Tenant(id="1", expires_at=date.today(), channels=["wa"])
    assert ds.resolve_channels(settings, tenant) == ["email"]


def test_deep_link():
    url = ds.build_renew_url("pro", "/admin", "T-3")
    assert "plan=pro" in url
    assert "return_to=%2Fadmin" in url
    assert "utm_campaign=T-3" in url
