from __future__ import annotations

"""GST calculation helpers for invoices.

This module centralises GST/HSN handling with precise ₹0.01 rounding.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Mapping

GSTMode = str  # "reg", "comp" or "unreg"

ROUND = Decimal("0.01")


def generate_invoice(
    items: Iterable[Mapping[str, object]],
    gst_mode: GSTMode,
    gstin: str | None = None,
    *,
    is_interstate: bool = False,
) -> dict:
    """Build an invoice dictionary with item and tax lines.

    Parameters
    ----------
    items:
        Iterable of mappings. Each mapping should include ``price`` and may
        define ``qty``, ``gst`` and ``hsn``.
    gst_mode:
        ``"reg"`` applies GST rates. ``"comp"`` and ``"unreg"`` skip tax lines.
    gstin:
        Optional GSTIN included when ``gst_mode`` is ``"reg"``.
    is_interstate:
        When ``True``, tax lines are reported as IGST instead of CGST/SGST.
    """

    subtotal = Decimal("0")
    tax_acc: defaultdict[Decimal, Decimal] = defaultdict(lambda: Decimal("0"))
    out_items: list[dict] = []

    for item in items:
        qty = Decimal(str(item.get("qty", 1)))
        price = Decimal(str(item["price"]))
        gst_rate = Decimal(str(item.get("gst", 0)))
        line_total = qty * price
        subtotal += line_total

        line = {"name": item.get("name"), "qty": int(qty), "price": float(price)}
        if gst_mode == "reg" and gst_rate:
            line["gst"] = float(gst_rate)
            if item.get("hsn"):
                line["hsn"] = item["hsn"]
            tax = line_total * gst_rate / Decimal("100")
            tax_acc[gst_rate] += tax
        out_items.append(line)

    subtotal = subtotal.quantize(ROUND, rounding=ROUND_HALF_UP)

    tax_lines: list[dict] = []
    total_tax = Decimal("0")
    if gst_mode == "reg":
        for rate, amount in tax_acc.items():
            amount = amount.quantize(ROUND, rounding=ROUND_HALF_UP)
            if is_interstate:
                tax_lines.append(
                    {"label": f"IGST {int(rate)}%", "amount": float(amount)}
                )
                total_tax += amount
            else:
                half_rate = float(rate) / 2
                half_amount = (amount / 2).quantize(ROUND, rounding=ROUND_HALF_UP)
                tax_lines.append(
                    {"label": f"CGST {half_rate}%", "amount": float(half_amount)}
                )
                tax_lines.append(
                    {"label": f"SGST {half_rate}%", "amount": float(half_amount)}
                )
                total_tax += half_amount * 2

    grand_total = (subtotal + total_tax).quantize(ROUND, rounding=ROUND_HALF_UP)

    invoice = {
        "gst_mode": gst_mode,
        "items": out_items,
        "subtotal": float(subtotal),
        "tax_lines": tax_lines,
        "grand_total": float(grand_total),
    }
    if gstin and gst_mode != "unreg":
        invoice["gstin"] = gstin
    return invoice
