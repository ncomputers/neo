from __future__ import annotations

"""Helpers for computing mid-cycle plan change proration."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import os

from ..tax import billing_gst

ROUND = Decimal("0.01")


def compute_proration(subscription, from_plan, to_plan, as_of: datetime) -> dict:
    """Compute proration for switching from ``from_plan`` to ``to_plan``.

    ``subscription`` must expose ``current_period_start``, ``current_period_end``,
    and optionally ``supplier_state_code`` and ``buyer_state_code`` for GST
    splitting.
    """

    period_secs = (
        subscription.current_period_end - subscription.current_period_start
    ).total_seconds()
    remaining_secs = (subscription.current_period_end - as_of).total_seconds()
    prorate_factor = max(0, remaining_secs / period_secs) if period_secs else 0

    delta = Decimal(str(to_plan.price_inr - from_plan.price_inr))
    proration_amount = (delta * Decimal(str(prorate_factor))).quantize(
        ROUND, rounding=ROUND_HALF_UP
    )

    tax_rate = Decimal(os.getenv("PRORATION_TAX_RATE", "0.18"))
    gross = (proration_amount * (Decimal(1) + tax_rate)).quantize(
        ROUND, rounding=ROUND_HALF_UP
    )
    supplier_state = getattr(subscription, "supplier_state_code", "00")
    buyer_state = getattr(subscription, "buyer_state_code", "00")
    tax_breakup = billing_gst.split_tax(gross, supplier_state, buyer_state, tax_rate)

    return {
        "proration_amount": proration_amount,
        "prorate_factor": prorate_factor,
        "tax_breakup": tax_breakup,
        "as_of": as_of,
    }
