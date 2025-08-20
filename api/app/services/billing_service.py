from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping, Literal

GSTMode = Literal["unreg", "comp", "reg"]


def _round_nearest_1(amount: Decimal) -> Decimal:
    """Round to nearest rupee using bankers rounding."""

    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def compute_bill(
    items: Iterable[Mapping[str, float]],
    gst_mode: GSTMode,
    rounding: str = "nearest_1",
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

    Returns
    -------
    dict
        ``{"subtotal": float, "tax_breakup": dict, "total": float}``

    Examples
    --------
    >>> items = [
    ...     {"qty": 2, "price": 100, "gst": 5},
    ...     {"qty": 1, "price": 200, "gst": 12},
    ... ]
    >>> compute_bill(items, "reg")
    {'subtotal': 400.0, 'tax_breakup': {5: 10.0, 12: 24.0}, 'total': 434.0}
    >>> compute_bill(items, "unreg")
    {'subtotal': 400.0, 'tax_breakup': {}, 'total': 400.0}
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

    if rounding == "nearest_1":
        total = _round_nearest_1(total)
    else:
        raise ValueError(f"Unsupported rounding mode: {rounding}")

    return {
        "subtotal": float(subtotal.quantize(Decimal("0.01"))),
        "tax_breakup": {int(rate): float(val.quantize(Decimal("0.01"))) for rate, val in tax_breakup.items()},
        "total": float(total.quantize(Decimal("0.01"))),
    }
