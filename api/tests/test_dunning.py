from datetime import date, timedelta
from api.app.dunning import (
    Tenant,
    build_renew_url,
    compute_template_key,
    schedule_dunning,
    should_show_banner,
)


def test_cadence_math():
    today = date(2023, 1, 1)
    assert compute_template_key(today + timedelta(days=7), today) == "T-7"
    assert compute_template_key(today + timedelta(days=3), today) == "T-3"
    assert compute_template_key(today + timedelta(days=1), today) == "T-1"
    assert compute_template_key(today, today) == "T+0"
    assert compute_template_key(today - timedelta(days=3), today) == "T+3"
    assert compute_template_key(today - timedelta(days=7), today) == "T+7"


def test_idempotency(tmp_path):
    t = Tenant(id="t1", subscription_expires_at=date.today())
    log = tmp_path / "log.jsonl"
    first = schedule_dunning([t], today=date.today(), log_path=log)
    second = schedule_dunning([t], today=date.today(), log_path=log)
    assert len(first) == 1
    assert second == []


def test_snooze_suppresses_banner():
    today = date.today()
    assert should_show_banner("GRACE", today - timedelta(days=1), today)
    assert not should_show_banner("GRACE", today, today)


def test_channel_opt_outs(tmp_path):
    t = Tenant(
        id="t1",
        subscription_expires_at=date.today(),
        email_opt_in=False,
        wa_opt_in=True,
        owner_phone="123",
    )
    events = schedule_dunning([t], today=date.today(), log_path=tmp_path / "l")
    assert events and events[0]["channels_sent"] == ["whatsapp"]


def test_deep_link_contains_plan_and_return():
    url = build_renew_url("pro", "/dashboard", "T-3")
    assert "plan=pro" in url
    assert "return_to=%2Fdashboard" in url
    assert url.endswith("utm_campaign=T-3")
