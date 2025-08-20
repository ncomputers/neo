from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import File, FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI()


class OrderRequest(BaseModel):
    tenant_id: str
    open_tables: int


TENANTS: dict[str, dict] = {}
PAYMENTS: dict[str, dict] = {}


@app.post("/tenants")
async def create_tenant(name: str, licensed_tables: int) -> dict[str, str]:
    tenant_id = str(uuid.uuid4())
    TENANTS[tenant_id] = {
        "name": name,
        "licensed_tables": licensed_tables,
        "subscription_expires_at": datetime.utcnow(),
    }
    return {"tenant_id": tenant_id}


@app.post("/orders")
async def create_order(request: OrderRequest) -> dict[str, str]:
    tenant = TENANTS.get(request.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if request.open_tables >= tenant["licensed_tables"]:
        raise HTTPException(status_code=403, detail="Licensed table limit exceeded")

    expiry = tenant["subscription_expires_at"]
    if datetime.utcnow() > expiry + timedelta(days=7):
        raise HTTPException(status_code=403, detail="Subscription expired")

    return {"status": "order accepted"}


@app.post("/tenants/{tenant_id}/subscription/renew")
async def renew_subscription(tenant_id: str, screenshot: UploadFile = File(...)) -> dict[str, str]:
    if tenant_id not in TENANTS:
        raise HTTPException(status_code=404, detail="Tenant not found")

    payment_id = str(uuid.uuid4())
    uploads = Path(__file__).resolve().parent / "payments"
    uploads.mkdir(exist_ok=True)
    file_path = uploads / f"{payment_id}_{screenshot.filename}"
    with file_path.open("wb") as buffer:
        buffer.write(await screenshot.read())

    PAYMENTS[payment_id] = {
        "tenant_id": tenant_id,
        "screenshot": str(file_path),
        "verified": False,
    }
    return {"payment_id": payment_id}


@app.post("/tenants/{tenant_id}/subscription/payments/{payment_id}/verify")
async def verify_payment(tenant_id: str, payment_id: str, months: int = 1) -> dict[str, str]:
    payment = PAYMENTS.get(payment_id)
    if payment is None or payment["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment["verified"] = True
    tenant = TENANTS[tenant_id]
    tenant["subscription_expires_at"] = tenant["subscription_expires_at"] + timedelta(
        days=30 * months
    )
    return {"status": "verified"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
