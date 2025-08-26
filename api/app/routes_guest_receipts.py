"""Expose guest receipt history when contact + consent is provided."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from .services.receipt_vault import ReceiptVault
from .utils.responses import ok

router = APIRouter(prefix="/guest")


async def require_contact(phone: str | None = None, email: str | None = None) -> str:
    """Validate that a contact identifier was supplied."""

    contact = phone or email
    if not contact:
        raise HTTPException(status_code=400, detail="contact required")
    return contact


@router.get("/receipts")
async def list_receipts(
    request: Request, contact: str = Depends(require_contact)
) -> dict:
    """Return the last ten redacted receipts for ``contact``."""

    vault = ReceiptVault(request.app.state.redis)
    receipts = await vault.list(contact)
    return ok({"receipts": receipts})


__all__ = ["router"]
