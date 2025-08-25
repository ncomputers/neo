"""Media upload endpoint using pluggable storage backends."""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image, ImageOps

from .auth import User, role_required
from .middlewares import licensing as lic_module
from .storage import storage
from .utils.responses import err, ok

router = APIRouter()

ALLOWED_TYPES = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/webp": "WEBP",
}
MAX_BYTES = 2 * 1024 * 1024
MAX_DIM = 4096


@router.post("/api/outlet/{tenant}/media/upload")
async def upload_media(
    tenant: str,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Validate and persist ``file`` and return its public URL and storage key."""

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "bad type")

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "too large")

    try:
        img = Image.open(BytesIO(contents))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid image") from exc

    if img.width > MAX_DIM or img.height > MAX_DIM:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "too big")
    if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no animation")

    img.info.pop("exif", None)
    img = ImageOps.exif_transpose(img)
    out = BytesIO()
    fmt = ALLOWED_TYPES[file.content_type]
    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs.update({"quality": 85, "optimize": True})
    elif fmt == "PNG":
        save_kwargs.update({"optimize": True})
    else:  # WEBP
        save_kwargs.update({"quality": 80})

    img.save(out, **save_kwargs)
    out.seek(0)

    tenant_obj = getattr(request.state, "tenant", None)
    limit_mb = (getattr(tenant_obj, "license_limits", {}) or {}).get(
        "max_images_mb"
    )
    if limit_mb is not None:
        used = lic_module.storage_bytes(tenant)
        if used + len(out.getvalue()) > limit_mb * 1024 * 1024:
            return JSONResponse(
                err("FEATURE_LIMIT", "image storage limit reached"),
                status_code=status.HTTP_403_FORBIDDEN,
            )

    processed = UploadFile(
        filename=file.filename, file=out, headers={"content-type": file.content_type}
    )

    url, key = await storage.save(tenant, processed)
    return ok({"url": url, "key": key})


__all__ = ["router"]
