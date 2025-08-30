from __future__ import annotations

import os
from decimal import Decimal
from datetime import datetime
from pathlib import Path

os.environ.setdefault("BILL_SUPPLIER_STATE_CODE", "27")
os.environ.setdefault("BILL_SUPPLIER_GSTIN", "27ABCDE1234F2Z5")
os.environ.setdefault("BILL_SAC_CODE", "998313")
os.environ.setdefault("BILL_INVOICE_SERIES", "SaaS")
os.environ.setdefault("BILL_CN_SERIES", "CN")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from api.app.tax.billing_gst import split_tax  # noqa: E402
from api.app.billing.invoice_service import (  # noqa: E402
    allocate_number,
    create_credit_note,
    create_invoice,
)
from api.app.db import SessionLocal  # noqa: E402
from api.app.routes_admin_billing import router as billing_router  # noqa: E402

test_app = FastAPI()
test_app.include_router(billing_router)
client = TestClient(test_app)


def test_split_tax_same_state() -> None:
    res = split_tax(Decimal("118"), "27", "27")
    assert res["cgst"] == Decimal("9.00")
    assert res["sgst"] == Decimal("9.00")
    assert res["igst"] == Decimal("0.00")
    assert res["taxable"] == Decimal("100.00")


def test_split_tax_inter_state() -> None:
    res = split_tax(Decimal("118"), "27", "29")
    assert res["igst"] == Decimal("18.00")
    assert res["cgst"] == Decimal("0.00")
    assert res["sgst"] == Decimal("0.00")


def test_allocate_number_fy_reset() -> None:
    n1, fy1 = allocate_number("SaaS", now=datetime(2030, 5, 1))
    n2, fy1b = allocate_number("SaaS", now=datetime(2030, 6, 1))
    n3, fy2 = allocate_number("SaaS", now=datetime(2031, 4, 1))
    assert n1.endswith("0001")
    assert n2.endswith("0002")
    assert fy1 == fy1b
    assert fy1 != fy2
    assert n3.endswith("0001")


def test_invoice_pdf_and_credit_note(tmp_path) -> None:
    period_start = datetime(2025, 4, 1)
    period_end = datetime(2025, 4, 30)
    inv_id = create_invoice(
        "tenant1",
        "plan1",
        period_start,
        period_end,
        Decimal("118"),
        buyer_gstin="27ABCDE1234F2Z5",
    )
    resp = client.get(f"/admin/billing/invoice/{inv_id}.pdf")
    assert resp.status_code == 200
    assert resp.content

    cn_id = create_credit_note(inv_id, Decimal("59"), "refund")
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT pdf_path FROM billing_credit_notes WHERE id=:id"),
            {"id": cn_id},
        ).fetchone()
    assert row and Path(row[0]).exists()


def test_invoices_csv() -> None:
    create_invoice(
        "tenant2",
        "plan1",
        datetime(2025, 5, 1),
        datetime(2025, 5, 31),
        Decimal("118"),
    )
    resp = client.get(
        "/admin/billing/invoices.csv?from=2025-01-01&to=2025-12-31"
    )
    assert resp.status_code == 200
    lines = resp.text.strip().splitlines()
    assert lines[0].startswith("id,number,amount_inr")
    assert len(lines) >= 2
