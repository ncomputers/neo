from __future__ import annotations

"""GST helpers for SaaS billing."""

from decimal import Decimal, ROUND_HALF_UP

ROUND = Decimal("0.01")


def split_tax(
    amount_inr: Decimal,
    supplier_state_code: str,
    buyer_state_code: str,
    tax_rate: Decimal = Decimal("0.18"),
) -> dict:
    """Split ``amount_inr`` into taxable value and GST components.

    Parameters
    ----------
    amount_inr:
        Total amount including GST.
    supplier_state_code:
        Two digit state code of the supplier.
    buyer_state_code:
        Two digit state code of the buyer.
    tax_rate:
        GST rate expressed as a decimal fraction (default ``0.18``).
    """

    taxable = (amount_inr / (1 + tax_rate)).quantize(ROUND, rounding=ROUND_HALF_UP)
    tax_total = (amount_inr - taxable).quantize(ROUND, rounding=ROUND_HALF_UP)
    cgst = sgst = igst = Decimal("0.00")
    if supplier_state_code == buyer_state_code:
        half = (tax_total / 2).quantize(ROUND, rounding=ROUND_HALF_UP)
        cgst = half
        sgst = tax_total - half
    else:
        igst = tax_total
    return {
        "taxable": taxable,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "rate": tax_rate,
    }
