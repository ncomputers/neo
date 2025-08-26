import pathlib
import sys
import uuid
from datetime import datetime

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import menu  # noqa: E402
from api.app.services import billing_service  # noqa: E402
from config import get_settings  # noqa: E402


def _reset_menu():
    menu._items.clear()


def test_discount_windows_apply(monkeypatch):
    monkeypatch.setenv("FLAG_HAPPY_HOUR", "1")
    windows = [
        {"days": ["mon"], "start": "10:00", "end": "11:00", "percent": 10},
        {"days": ["mon"], "start": "11:00", "end": "12:00", "flat": 15},
        {"days": ["mon"], "start": "12:00", "end": "13:00", "percent": 50},
    ]
    settings = get_settings()
    settings.happy_hour_windows = windows

    _reset_menu()
    iid = uuid.uuid4()
    menu._items[iid] = menu.Item(id=iid, name="Tea", price=100, category_id=None)

    item = {"price": 100, "qty": 1}
    b1 = billing_service.compute_bill(
        [item],
        "unreg",
        happy_hour_windows=windows,
        now=datetime(2023, 1, 2, 10, 30),
    )
    b2 = billing_service.compute_bill(
        [item],
        "unreg",
        happy_hour_windows=windows,
        now=datetime(2023, 1, 2, 11, 30),
    )
    b3 = billing_service.compute_bill(
        [item],
        "unreg",
        happy_hour_windows=windows,
        now=datetime(2023, 1, 2, 12, 30),
    )

    assert b1["total"] == 90.0
    assert b2["total"] == 85.0
    assert b3["total"] == 50.0

    resp = menu.list_items(now=datetime(2023, 1, 2, 10, 30))
    data = resp["data"][0].model_dump()
    assert data["price"] == 90
    assert data["strike_price"] == 100


def test_discount_boundary(monkeypatch):
    monkeypatch.setenv("FLAG_HAPPY_HOUR", "1")
    windows = [{"days": ["mon"], "start": "10:00", "end": "11:00", "percent": 10}]
    settings = get_settings()
    settings.happy_hour_windows = windows
    item = {"price": 100, "qty": 1}

    at_start = billing_service.compute_bill(
        [item],
        "unreg",
        happy_hour_windows=windows,
        now=datetime(2023, 1, 2, 10, 0),
    )
    at_end = billing_service.compute_bill(
        [item],
        "unreg",
        happy_hour_windows=windows,
        now=datetime(2023, 1, 2, 11, 0),
    )

    assert at_start["total"] == 90.0
    assert at_end["total"] == 100.0


def test_discount_overlap_uses_best(monkeypatch):
    monkeypatch.setenv("FLAG_HAPPY_HOUR", "1")
    windows = [
        {"days": ["mon"], "start": "10:00", "end": "12:00", "percent": 10},
        {"days": ["mon"], "start": "11:00", "end": "13:00", "flat": 15},
    ]
    settings = get_settings()
    settings.happy_hour_windows = windows
    item = {"price": 100, "qty": 1}
    bill = billing_service.compute_bill(
        [item],
        "unreg",
        happy_hour_windows=windows,
        now=datetime(2023, 1, 2, 11, 30),
    )
    assert bill["total"] == 85.0


def test_invoice_context_includes_discount(monkeypatch):
    monkeypatch.setenv("FLAG_HAPPY_HOUR", "1")
    windows = [{"days": ["mon"], "start": "10:00", "end": "11:00", "percent": 10}]
    settings = get_settings()
    settings.happy_hour_windows = windows
    items = [{"price": 100, "qty": 1}]

    invoice = billing_service.build_invoice_context(
        items,
        "unreg",
        happy_hour_windows=windows,
        now=datetime(2023, 1, 2, 10, 30),
    )

    assert invoice["discount"] == 10.0
    assert invoice["grand_total"] == 90.0


def test_coupons_rejected_during_happy_hour(monkeypatch):
    monkeypatch.setenv("FLAG_HAPPY_HOUR", "1")
    windows = [{"days": ["mon"], "start": "10:00", "end": "11:00", "percent": 10}]
    settings = get_settings()
    settings.happy_hour_windows = windows
    item = {"price": 100}
    coupon = {"code": "A", "percent": 10}
    with pytest.raises(billing_service.CouponError) as exc:
        billing_service.compute_bill(
            [item],
            "unreg",
            coupons=[coupon],
            happy_hour_windows=windows,
            now=datetime(2023, 1, 2, 10, 30),
        )
    assert exc.value.code == "HAPPY_HOUR"
    assert exc.value.hint == "Try again outside happy hour"
