"""Media upload endpoint using pluggable storage backends."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from .auth import User, role_required
from .storage import storage
from .utils.responses import ok

router = APIRouter()


@router.post("/api/outlet/{tenant}/media/upload")
async def upload_media(
    tenant: str,
    file: UploadFile = File(...),
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Persist ``file`` and return its public URL and storage key."""

    url, key = await storage.save(tenant, file)
    return ok({"url": url, "key": key})


__all__ = ["router"]
