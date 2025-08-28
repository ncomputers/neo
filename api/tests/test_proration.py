from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import os

os.environ.setdefault("PRORATION_TAX_RATE", "0.18")

from api.app.billing.proration import compute_proration


@dataclass
class Plan:
    price_inr: int


@dataclass
class Subscription:
    current_period_start: datetime
    current_period_end: datetime
    supplier_state_code: str = "27"
    buyer_state_code: str = "27"


def _sample_subscription() -> Subscription:
    start = datetime(2025, 1, 1)
    end = start + timedelta(days=30)
    return Subscription(start, end)


def test_proration_same_plan() -> None:
    sub = _sample_subscription()
    plan = Plan(price_inr=5000)
    res = compute_proration(sub, plan, plan, as_of=sub.current_period_start)
    assert res["proration_amount"] == Decimal("0.00")
    assert res["tax_breakup"]["cgst"] == Decimal("0.00")


def test_proration_free_to_paid_midcycle() -> None:
    sub = _sample_subscription()
    from_plan = Plan(price_inr=0)
    to_plan = Plan(price_inr=5000)
    mid = (
        sub.current_period_start
        + (sub.current_period_end - sub.current_period_start) / 2
    )
    res = compute_proration(sub, from_plan, to_plan, as_of=mid)
    assert res["proration_amount"] == Decimal("2500.00")
    assert res["tax_breakup"]["cgst"] == Decimal("225.00")
    assert res["tax_breakup"]["sgst"] == Decimal("225.00")


def test_proration_paid_to_free_midcycle() -> None:
    sub = _sample_subscription()
    from_plan = Plan(price_inr=5000)
    to_plan = Plan(price_inr=0)
    mid = (
        sub.current_period_start
        + (sub.current_period_end - sub.current_period_start) / 2
    )
    res = compute_proration(sub, from_plan, to_plan, as_of=mid)
    assert res["proration_amount"] == Decimal("-2500.00")
    assert res["tax_breakup"]["cgst"] == Decimal("-225.00")
    assert res["tax_breakup"]["sgst"] == Decimal("-225.00")


def test_proration_last_minute_rounds_to_zero() -> None:
    sub = _sample_subscription()
    from_plan = Plan(price_inr=3000)
    to_plan = Plan(price_inr=5000)
    as_of = sub.current_period_end - timedelta(seconds=1)
    res = compute_proration(sub, from_plan, to_plan, as_of=as_of)
    assert res["proration_amount"] == Decimal("0.00")
