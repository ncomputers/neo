from __future__ import annotations

"""PDF rendering for billing invoices and credit notes."""

import importlib
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from sqlalchemy import text
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..db import SessionLocal

ROOT_DIR = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = ROOT_DIR / "templates"
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape())
STORAGE_DIR = ROOT_DIR / "storage" / "billing_invoices"


def _html_to_pdf(html: str, out_path: Path) -> None:
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf = weasyprint.HTML(string=html, base_url=str(ROOT_DIR)).write_pdf()
        out_path.write_bytes(pdf)
        return
    except Exception:
        pass
    try:
        pisa = importlib.import_module("xhtml2pdf.pisa")
        with open(out_path, "wb") as f:
            pisa.CreatePDF(html, dest=f)
        return
    except Exception:
        pass
    out_path.write_text(html, encoding="utf-8")


def _amount_words(amount: Decimal) -> str:
    return f"{amount} rupees"


def render_invoice_pdf(invoice_id: int) -> str:
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT tenant_id, number, fy_code, amount_inr, cgst_inr, sgst_inr, igst_inr,
                       supplier_gstin, buyer_gstin, sac_code, period_start, period_end
                FROM billing_invoices WHERE id=:id
                """
            ),
            {"id": invoice_id},
        ).fetchone()
        if not row:
            raise ValueError("invoice not found")
    period_start = datetime.fromisoformat(row[10])
    context = {
        "tenant_id": row[0],
        "number": row[1],
        "amount": Decimal(str(row[3])),
        "cgst": Decimal(str(row[4])),
        "sgst": Decimal(str(row[5])),
        "igst": Decimal(str(row[6])),
        "supplier_gstin": row[7],
        "buyer_gstin": row[8],
        "sac_code": row[9],
        "period_start": period_start.date(),
        "period_end": datetime.fromisoformat(row[11]).date(),
    }
    context["total"] = context["amount"]
    context["words"] = _amount_words(context["total"])
    html = _env.get_template("billing_invoice.html").render(invoice=context)
    out_dir = STORAGE_DIR / str(context["tenant_id"]) / str(period_start.year)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = context["number"].replace("/", "_") + ".pdf"
    out_path = out_dir / filename
    _html_to_pdf(html, out_path)
    return str(out_path)


def render_credit_note_pdf(credit_note_id: int) -> str:
    with SessionLocal() as db:
        cn = db.execute(
            text(
                "SELECT invoice_id, number, amount_inr, reason FROM billing_credit_notes WHERE id=:id"
            ),
            {"id": credit_note_id},
        ).fetchone()
        if not cn:
            raise ValueError("credit note not found")
        inv = db.execute(
            text(
                """
                SELECT tenant_id, number, amount_inr, supplier_gstin, buyer_gstin, sac_code, period_start
                FROM billing_invoices WHERE id=:id
                """
            ),
            {"id": cn[0]},
        ).fetchone()
    period_start = datetime.fromisoformat(inv[6])
    context = {
        "tenant_id": inv[0],
        "number": cn[1],
        "invoice_number": inv[1],
        "amount": Decimal(str(cn[2])),
        "reason": cn[3],
        "supplier_gstin": inv[3],
        "buyer_gstin": inv[4],
        "sac_code": inv[5],
    }
    context["words"] = _amount_words(context["amount"])
    html = _env.get_template("billing_credit_note.html").render(note=context)
    out_dir = STORAGE_DIR / str(context["tenant_id"]) / str(period_start.year)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = context["number"].replace("/", "_") + ".pdf"
    out_path = out_dir / filename
    _html_to_pdf(html, out_path)
    return str(out_path)
