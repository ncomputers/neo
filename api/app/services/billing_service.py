from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping, Literal, Sequence

GSTMode = Literal["unreg", "comp", "reg"]


class CouponError(ValueError):
    """Raised when coupon application fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _round_nearest_1(amount: Decimal) -> Decimal:
    """Round to nearest rupee using bankers rounding."""

    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def compute_bill(
    items: Iterable[Mapping[str, float]],
    gst_mode: GSTMode,
    rounding: str = "nearest_1",
    tip: float | Decimal | None = 0,
    coupons: Sequence[Mapping[str, object]] | None = None,
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

    tip_amount = Decimal(str(tip or 0))

    total = subtotal + sum(tax_breakup.values())

    applied_coupons: list[str] = []
    effective_discount = Decimal("0")
    if coupons:
        if len(coupons) > 1 and any(not c.get("is_stackable") for c in coupons):
            bad = next(c["code"] for c in coupons if not c.get("is_stackable"))
            raise CouponError("NON_STACKABLE", f"Coupon {bad} cannot be stacked")

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
        rounded_total = _round_nearest_1(total)
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
        "subtotal": float(subtotal.quantize(Decimal("0.01"))),
        "tax_breakup": {
            int(rate): float(val.quantize(Decimal("0.01")))
            for rate, val in tax_breakup.items()
        },
        "tip": float(tip_amount.quantize(Decimal("0.01"))),
        "rounding_adjustment": float(rounding_adjustment.quantize(Decimal("0.01"))),
        "total": float(rounded_total.quantize(Decimal("0.01"))),
    }

    if coupons:
        bill["applied_coupons"] = applied_coupons
        bill["effective_discount"] = float(effective_discount.quantize(Decimal("0.01")))

    return bill


def build_invoice_context(
    items: Iterable[Mapping[str, object]],
    gst_mode: GSTMode,
    gstin: str | None = None,
) -> dict:
    """Build a render-friendly invoice dict based on ``gst_mode``.

    Parameters
    ----------
    items:
        Each mapping should include ``name`` and ``price``. Optional keys
        include ``qty`` and ``hsn``.
    gst_mode:
        Tax mode for the invoice (``"reg"``, ``"comp"`` or ``"unreg"``).
    gstin:
        Optional GSTIN to include on the invoice header for registered modes.
    """

    bill = compute_bill(items, gst_mode)
    invoice = {
        "gst_mode": gst_mode,
        "items": [],
        "subtotal": bill["subtotal"],
        "tax_lines": [],
        "grand_total": bill["total"],
    }

    if bill.get("rounding_adjustment"):
        invoice["rounding_adjustment"] = bill["rounding_adjustment"]

    if gstin and gst_mode != "unreg":
        invoice["gstin"] = gstin

    for item in items:
        line = {
            "name": item.get("name"),
            "qty": item.get("qty", 1),
            "price": item.get("price"),
        }
        if gst_mode == "reg" and item.get("hsn"):
            line["hsn"] = item.get("hsn")
        invoice["items"].append(line)

    if gst_mode == "reg":
        for rate, amount in bill["tax_breakup"].items():
            half_rate = rate / 2
            half_amount = round(amount / 2, 2)
            invoice["tax_lines"].append(
                {"label": f"CGST {half_rate}%", "amount": half_amount}
            )
            invoice["tax_lines"].append(
                {"label": f"SGST {half_rate}%", "amount": half_amount}
            )
    elif gst_mode == "comp":
        total_tax = round(bill["total"] - bill["subtotal"], 2)
        invoice["tax_lines"].append(
            {"label": "Composition Tax Included", "amount": total_tax}
        )

    return invoice
