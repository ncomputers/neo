from __future__ import annotations

"""Admin endpoints for validating menu CSV uploads."""

import csv
from io import StringIO
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile

from .auth import User, role_required

router = APIRouter()

REQUIRED_FIELDS = ["name", "price"]


@router.post("/api/outlet/{tenant_id}/menu/import/dryrun")
async def menu_import_dryrun(
    tenant_id: str,
    file: UploadFile = File(...),
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Validate a CSV file without mutating the database.

    Returns ``ok`` along with any ``warnings`` or ``errors`` detected. Also
    reports ``missing_fields`` from the CSV header and a placeholder
    ``inferred_hsn`` list for future enhancements.
    """

    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(StringIO(content))

    missing_fields = [f for f in REQUIRED_FIELDS if f not in (reader.fieldnames or [])]
    warnings: List[str] = []
    errors: List[str] = []
    inferred_hsn: List[str] = []

    if missing_fields:
        errors.append("missing_required_fields")
    else:
        for idx, row in enumerate(reader, start=2):
            for field in REQUIRED_FIELDS:
                if not row.get(field):
                    errors.append(f"row {idx} missing {field}")

    return {
        "ok": True,
        "warnings": warnings,
        "errors": errors,
        "inferred_hsn": inferred_hsn,
        "missing_fields": missing_fields,
    }
