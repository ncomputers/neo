from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Iterable, Literal, Mapping, Sequence

from ..pricing import active_windows, apply_discount
from .. import flags
from ..tax.gst_engine import generate_invoice

GSTMode = Literal["unreg", "comp", "reg"]


class CouponError(ValueError):
    """Raised when coupon application fails."""

    def __init__(self, code: str, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.hint = hint


ROUNDING_MAP = {
    "half-up": ROUND_HALF_UP,
    "bankers": ROUND_HALF_EVEN,
    "ceil": ROUND_CEILING,
    "floor": ROUND_FLOOR,
}


def _round_nearest_1(amount: Decimal, mode: str) -> Decimal:
    """Round to nearest rupee using the given rounding ``mode``."""

    try:
        rounding = ROUNDING_MAP[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported rounding mode: {mode}") from exc
    return amount.quantize(Decimal("1"), rounding=rounding)


def compute_bill(
    items: Iterable[Mapping[str, float]],
    gst_mode: GSTMode,
    rounding: str = "nearest_1",
    tip: float | Decimal | None = 0,
    coupons: Sequence[Mapping[str, object]] | None = None,
    gst_rounding: str = "invoice-total",
    rounding_mode: str = "half-up",
    happy_hour_windows: Sequence[Mapping[str, object]] | None = None,
    now: datetime | time | None = None,
) -> dict:
    """Compute subtotal, tax breakup and total for a list of items.

    Each item mapping should contain ``price`` and may define ``qty`` and ``gst``.

    Parameters
    ----------
    items:
        Iterable of mappings. ``price`` is required, ``qty`` defaults to ``1`` and
        ``gst`` (percentage) defaults to ``0``.
    gst_mode:
        ``"reg"`` applies the GST rates. ``"unreg"`` and ``"comp"`` ignore GST.
    rounding:
        Rounding policy for the grand total. ``"nearest_1"``/``"nearest"``
        rounds to the nearest rupee, while ``"none"`` skips rounding.
    coupons:
        Optional sequence of coupon mappings. Each mapping may include ``code``,
        ``percent``, ``flat``, ``is_stackable`` and ``max_discount``.
    tip:
        Optional tip amount applied after tax and discounts.


    Returns
    -------
    dict
        Bill summary including ``subtotal``, ``tax_breakup``,
        ``rounding_adjustment`` and ``total``. When coupons are provided,
        ``applied_coupons`` and ``effective_discount`` are included.


    Examples
    --------
    >>> items = [
    ...     {"qty": 2, "price": 100, "gst": 5},
    ...     {"qty": 1, "price": 200, "gst": 12},
    ... ]
    >>> compute_bill(items, "reg")
    {'subtotal': 400.0, 'tax_breakup': {5: 10.0, 12: 24.0}, 'tip': 0.0, 'total': 434.0}
    >>> compute_bill(items, "unreg", tip=10)
    {'subtotal': 400.0, 'tax_breakup': {}, 'tip': 10.0, 'total': 410.0}
    """

    subtotal = Decimal("0")
    discount_total = Decimal("0")
    tax_breakup: defaultdict[Decimal, Decimal] = defaultdict(lambda: Decimal("0"))

    if rounding_mode not in ROUNDING_MAP:
        raise ValueError(f"Unsupported rounding mode: {rounding_mode}")
    rounding_constant = ROUNDING_MAP[rounding_mode]

    if gst_rounding not in {"item-wise", "invoice-total"}:
        raise ValueError(f"Unsupported GST rounding style: {gst_rounding}")

    windows = []
    if flags.get("happy_hour"):
        windows = active_windows(happy_hour_windows, now)
    if windows and coupons:
        raise CouponError(
            "HAPPY_HOUR",
            "Coupons cannot be used during happy hour",
            hint="Try again outside happy hour",
        )
    for item in items:
        qty = Decimal(str(item.get("qty", 1)))
        price = Decimal(str(item["price"]))
        gst_rate = Decimal(str(item.get("gst", 0)))
        line_total = qty * price
        subtotal += line_total
        discounted_price = apply_discount(price, windows)
        discount_total += (price - discounted_price) * qty
        discounted_total = qty * discounted_price
        if gst_mode == "reg" and gst_rate:
            tax = discounted_total * gst_rate / Decimal("100")
            if gst_rounding == "item-wise":
                tax = tax.quantize(Decimal("0.01"), rounding=rounding_constant)
            tax_breakup[gst_rate] += tax

    tip_amount = Decimal(str(tip or 0))

    if gst_rounding == "invoice-total":
        for rate in list(tax_breakup.keys()):
            tax_breakup[rate] = tax_breakup[rate].quantize(
                Decimal("0.01"), rounding=rounding_constant
            )

    total = (subtotal - discount_total) + sum(tax_breakup.values())

    applied_coupons: list[str] = []
    effective_discount = Decimal("0")
    if coupons:
        if len(coupons) > 1 and any(not c.get("is_stackable") for c in coupons):
            bad = next(c["code"] for c in coupons if not c.get("is_stackable"))
            raise CouponError(
                "NON_STACKABLE",
                f"Coupon {bad} cannot be stacked",
                hint="Remove non-stackable coupon",
            )

        percent_total = Decimal("0")
        flat_total = Decimal("0")
        for c in coupons:
            applied_coupons.append(str(c.get("code", "")))
            if c.get("percent"):
                percent_total += total * Decimal(str(c["percent"])) / Decimal("100")
            if c.get("flat"):
                flat_total += Decimal(str(c["flat"]))
        discount = percent_total + flat_total

        caps = [
            Decimal(str(c["max_discount"]))
            for c in coupons
            if c.get("max_discount") is not None
        ]
        if caps:
            cap = min(caps)
            if discount > cap:
                discount = cap

        total -= discount

    total += tip_amount

    if rounding in {"nearest_1", "nearest"}:
        rounded_total = _round_nearest_1(total, rounding_mode)
    elif rounding in {"none", "off"}:
        rounded_total = total
    else:
        raise ValueError(f"Unsupported rounding mode: {rounding}")

    rounding_adjustment = rounded_total - total

    if coupons:
        effective_discount = (subtotal + sum(tax_breakup.values())) - (
            rounded_total - tip_amount
        )

    bill = {
        "subtotal": float(
            subtotal.quantize(Decimal("0.01"), rounding=rounding_constant)
        ),
        "tax_breakup": {
            int(rate): float(val.quantize(Decimal("0.01"), rounding=rounding_constant))
            for rate, val in tax_breakup.items()
        },
        "tip": float(tip_amount.quantize(Decimal("0.01"), rounding=rounding_constant)),
        "rounding_adjustment": float(
            rounding_adjustment.quantize(Decimal("0.01"), rounding=rounding_constant)
        ),
        "total": float(
            rounded_total.quantize(Decimal("0.01"), rounding=rounding_constant)
        ),
    }

    if coupons:
        bill["applied_coupons"] = applied_coupons
        bill["effective_discount"] = float(effective_discount.quantize(Decimal("0.01")))
    if discount_total:
        bill["discount"] = float(
            discount_total.quantize(Decimal("0.01"), rounding=rounding_constant)
        )

    return bill


def build_invoice_context(
    items: Iterable[Mapping[str, object]],
    gst_mode: GSTMode,
    gstin: str | None = None,
    rounding: str = "nearest_1",
    gst_rounding: str = "invoice-total",
    rounding_mode: str = "half-up",
    happy_hour_windows: Sequence[Mapping[str, object]] | None = None,
    now: datetime | time | None = None,
    is_interstate: bool = False,
) -> dict:
    """Build a render-friendly invoice dict based on ``gst_mode``.

    The heavy lifting is delegated to :func:`tax.gst_engine.generate_invoice`.
    Parameters unrelated to GST are accepted for backward compatibility but
    ignored.
    """

    return generate_invoice(items, gst_mode, gstin=gstin, is_interstate=is_interstate)
