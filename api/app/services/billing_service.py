from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping, Literal, Sequence

GSTMode = Literal["unreg", "comp", "reg"]


def _round_nearest_1(amount: Decimal) -> Decimal:
    """Round to nearest rupee using bankers rounding."""

    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def compute_bill(
    items: Iterable[Mapping[str, float]],
    gst_mode: GSTMode,
    rounding: str = "nearest_1",
    coupons: Sequence[Mapping[str, object]] | None = None,
    tip: float | Decimal | None = 0,
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
        Currently only ``"nearest_1"`` is supported.
    coupons:
        Optional sequence of coupon mappings. Each mapping may include ``code``,
        ``percent``, ``flat``, ``is_stackable`` and ``max_discount``.
    tip:
        Optional tip amount applied after tax and discounts.


    Returns
    -------
    dict
        Bill summary including ``subtotal``, ``tax_breakup`` and ``total``. When
        coupons are provided, ``applied_coupons`` and ``effective_discount`` are
        included.


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
    tax_breakup: defaultdict[Decimal, Decimal] = defaultdict(lambda: Decimal("0"))

    for item in items:
        qty = Decimal(str(item.get("qty", 1)))
        price = Decimal(str(item["price"]))
        gst_rate = Decimal(str(item.get("gst", 0)))
        line_total = qty * price
        subtotal += line_total
        if gst_mode == "reg" and gst_rate:
            tax = line_total * gst_rate / Decimal("100")
            tax_breakup[gst_rate] += tax

    total = subtotal + sum(tax_breakup.values())

    applied_coupons: list[str] = []
    effective_discount = Decimal("0")
    if coupons:
        if len(coupons) > 1 and any(not c.get("is_stackable") for c in coupons):
            bad = next(c["code"] for c in coupons if not c.get("is_stackable"))
            raise ValueError(f"Coupon {bad} cannot be stacked")

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

    if rounding == "nearest_1":
        rounded_total = _round_nearest_1(total)
    else:
        raise ValueError(f"Unsupported rounding mode: {rounding}")

    if coupons:
        effective_discount = (subtotal + sum(tax_breakup.values())) - rounded_total

    tip_amount = Decimal(str(tip or 0))
    total_with_tip = rounded_total + tip_amount

    bill = {
        "subtotal": float(subtotal.quantize(Decimal("0.01"))),
        "tax_breakup": {
            int(rate): float(val.quantize(Decimal("0.01")))
            for rate, val in tax_breakup.items()
        },
        "tip": float(tip_amount.quantize(Decimal("0.01"))),
        "total": float(total_with_tip.quantize(Decimal("0.01"))),
    }

    if coupons:
        bill["applied_coupons"] = applied_coupons
        bill["effective_discount"] = float(effective_discount.quantize(Decimal("0.01")))

    return bill
