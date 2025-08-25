"""Support contact information."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/support/contact")
async def support_contact() -> dict:
    """Return support contact details."""
    return {
        "email": "support@example.com",
        "phone": "+1-800-555-0199",
        "hours": "09:00-18:00 IST",
        "docs_url": "https://docs.example.com",
    }
