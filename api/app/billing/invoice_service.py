from __future__ import annotations

"""Service helpers for GST billing invoices and credit notes."""

from datetime import datetime
from decimal import Decimal
import os
from sqlalchemy import text

from ..db import SessionLocal
from ..tax.billing_gst import split_tax
from ..pdf.billing_pdf import render_invoice_pdf, render_credit_note_pdf

ROUND_CTX = Decimal("0.01")


def _fy_code(now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    start_year = now.year if now.month >= 4 else now.year - 1
    return f"{start_year}-{str(start_year + 1)[2:]}"


def allocate_number(series: str, now: datetime | None = None) -> tuple[str, str]:
    """Allocate the next invoice/credit note number for ``series``."""

    fy = _fy_code(now)
    with SessionLocal() as db:
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS billing_series(
                    series TEXT NOT NULL,
                    fy_code TEXT NOT NULL,
                    seq INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(series, fy_code)
                )
                """
            )
        )
        row = db.execute(
            text(
                "SELECT seq FROM billing_series WHERE series=:s AND fy_code=:f"
            ),
            {"s": series, "f": fy},
        ).fetchone()
        if row:
            seq = row[0] + 1
            db.execute(
                text(
                    "UPDATE billing_series SET seq=:seq WHERE series=:s AND fy_code=:f"
                ),
                {"seq": seq, "s": series, "f": fy},
            )
        else:
            seq = 1
            db.execute(
                text(
                    "INSERT INTO billing_series(series, fy_code, seq) VALUES (:s,:f,:seq)"
                ),
                {"s": series, "f": fy, "seq": seq},
            )
        db.commit()
    number = f"{series}/{fy}/{seq:04d}"
    return number, fy


def _ensure_invoice_table(db) -> None:
    db.execute(text("DROP TABLE IF EXISTS billing_invoices"))
    db.execute(
        text(
            """
            CREATE TABLE billing_invoices(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT,
                period_start TEXT,
                period_end TEXT,
                amount_inr NUMERIC(10,2),
                number TEXT,
                fy_code TEXT,
                place_of_supply TEXT,
                supplier_gstin TEXT,
                buyer_gstin TEXT,
                sac_code TEXT,
                cgst_inr NUMERIC(10,2),
                sgst_inr NUMERIC(10,2),
                igst_inr NUMERIC(10,2),
                pdf_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _ensure_credit_table(db) -> None:
    db.execute(text("DROP TABLE IF EXISTS billing_credit_notes"))
    db.execute(
        text(
            """
            CREATE TABLE billing_credit_notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER REFERENCES billing_invoices(id) ON DELETE CASCADE,
                number TEXT,
                fy_code TEXT,
                amount_inr NUMERIC(10,2),
                tax_inr NUMERIC(10,2),
                reason TEXT,
                pdf_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def create_invoice(
    tenant_id,
    plan_id,
    period_start,
    period_end,
    amount_inr,
    buyer_gstin: str | None = None,
):
    """Create an invoice row and render its PDF."""

    amount = Decimal(str(amount_inr))
    supplier_state = os.getenv("BILL_SUPPLIER_STATE_CODE", "00")
    supplier_gstin = os.getenv("BILL_SUPPLIER_GSTIN", "")
    sac_code = os.getenv("BILL_SAC_CODE", "")
    series = os.getenv("BILL_INVOICE_SERIES", "SaaS")

    number, fy = allocate_number(series)
    buyer_state = buyer_gstin[:2] if buyer_gstin else supplier_state
    tax = split_tax(amount, supplier_state, buyer_state)

    with SessionLocal() as db:
        _ensure_invoice_table(db)
        params = {
            "tenant_id": tenant_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "amount_inr": float(amount),
            "number": number,
            "fy_code": fy,
            "pos": buyer_state,
            "supplier_gstin": supplier_gstin,
            "buyer_gstin": buyer_gstin,
            "sac": sac_code,
            "cgst": float(tax["cgst"]),
            "sgst": float(tax["sgst"]),
            "igst": float(tax["igst"]),
        }
        res = db.execute(
            text(
                """
                INSERT INTO billing_invoices(
                    tenant_id, period_start, period_end, amount_inr,
                    number, fy_code, place_of_supply, supplier_gstin, buyer_gstin,
                    sac_code, cgst_inr, sgst_inr, igst_inr
                ) VALUES (
                    :tenant_id, :period_start, :period_end, :amount_inr,
                    :number, :fy_code, :pos, :supplier_gstin, :buyer_gstin,
                    :sac, :cgst, :sgst, :igst
                )
                """
            ),
            params,
        )
        invoice_id = res.lastrowid
        db.commit()

    pdf_path = render_invoice_pdf(invoice_id)
    with SessionLocal() as db:
        db.execute(
            text("UPDATE billing_invoices SET pdf_path=:p WHERE id=:id"),
            {"p": pdf_path, "id": invoice_id},
        )
        db.commit()
    return invoice_id


def create_credit_note(invoice_id: int, amount_inr, reason: str):
    """Create a credit note for ``invoice_id``."""

    amount = Decimal(str(amount_inr))
    series = os.getenv("BILL_CN_SERIES", "CN")

    with SessionLocal() as db:
        _ensure_credit_table(db)
        inv = db.execute(
            text(
                "SELECT tenant_id, supplier_gstin, place_of_supply FROM billing_invoices WHERE id=:id"
            ),
            {"id": invoice_id},
        ).fetchone()
        if not inv:
            raise ValueError("invoice not found")
        supplier_gstin = inv[1] or os.getenv("BILL_SUPPLIER_GSTIN", "")
        supplier_state = supplier_gstin[:2] if supplier_gstin else os.getenv("BILL_SUPPLIER_STATE_CODE", "00")
        buyer_state = inv[2]
    number, fy = allocate_number(series)
    tax = split_tax(amount, supplier_state, buyer_state)
    tax_total = tax["cgst"] + tax["sgst"] + tax["igst"]

    with SessionLocal() as db:
        res = db.execute(
            text(
                """
                INSERT INTO billing_credit_notes(
                    invoice_id, number, fy_code, amount_inr, tax_inr, reason
                ) VALUES (
                    :invoice_id, :number, :fy_code, :amount_inr, :tax_inr, :reason
                )
                """
            ),
            {
                "invoice_id": invoice_id,
                "number": number,
                "fy_code": fy,
                "amount_inr": float(amount),
                "tax_inr": float(tax_total),
                "reason": reason,
            },
        )
        cn_id = res.lastrowid
        db.commit()

    pdf_path = render_credit_note_pdf(cn_id)
    with SessionLocal() as db:
        db.execute(
            text("UPDATE billing_credit_notes SET pdf_path=:p WHERE id=:id"),
            {"p": pdf_path, "id": cn_id},
        )
        db.commit()
    return cn_id
