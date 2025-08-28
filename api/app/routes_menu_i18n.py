from __future__ import annotations

import csv
import io
import re
from contextlib import asynccontextmanager
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .models_tenant import MenuItem, TenantMeta
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    engine = get_engine(tenant_id)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with maker() as session:
            yield session
    finally:
        await engine.dispose()


@router.post("/api/outlet/{tenant_id}/menu/i18n/import")
@audit("i18n.import")
async def import_menu_i18n(
    tenant_id: str,
    file: UploadFile = File(...),
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    data = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(data))
    updated = 0
    skipped = 0
    errors: List[str] = []
    async with _session(tenant_id) as session:
        enabled = await session.scalar(select(TenantMeta.enabled_langs)) or ["en"]
        for row in reader:
            try:
                item_id = int(row.get("item_id", ""))
            except ValueError:
                skipped += 1
                errors.append(f"row {reader.line_num} invalid_item_id")
                continue
            lang = row.get("lang")
            if lang not in enabled:
                skipped += 1
                errors.append(f"row {reader.line_num} unsupported_lang")
                continue
            item = await session.get(MenuItem, item_id)
            if not item:
                skipped += 1
                errors.append(f"row {reader.line_num} missing_item")
                continue
            ni = item.name_i18n or {}
            di = item.desc_i18n or {}
            if row.get("name"):
                ni[lang] = row["name"]
            if row.get("description"):
                di[lang] = row["description"]
            item.name_i18n = ni
            item.desc_i18n = di
            updated += 1
        await session.commit()
    return ok({"updated_rows": updated, "skipped": skipped, "errors": errors})


@router.get("/api/outlet/{tenant_id}/menu/i18n/export")
@audit("i18n.export")
async def export_menu_i18n(
    tenant_id: str,
    langs: str | None = None,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
):
    async with _session(tenant_id) as session:
        enabled = await session.scalar(select(TenantMeta.enabled_langs)) or ["en"]
        requested = [c for c in (langs.split(",") if langs else enabled) if c]
        for code in requested:
            if code not in enabled:
                raise HTTPException(status_code=400, detail="unsupported language")
        result = await session.execute(select(MenuItem))
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["item_id", "lang", "name", "description"]
        )
        writer.writeheader()
        for item in result.scalars():
            for code in requested:
                name = (item.name_i18n or {}).get(code)
                desc = (item.desc_i18n or {}).get(code)
                if name or desc:
                    writer.writerow(
                        {
                            "item_id": item.id,
                            "lang": code,
                            "name": name,
                            "description": desc,
                        }
                    )
        output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv")


class I18nSettings(BaseModel):
    default_lang: str
    enabled_langs: List[str]


@router.patch("/api/outlet/{tenant_id}/settings/i18n")
@audit("i18n.settings")
async def update_i18n_settings(
    tenant_id: str,
    payload: I18nSettings,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    if any(not re.fullmatch(r"[a-z]{2}", code) for code in payload.enabled_langs):
        raise HTTPException(status_code=400, detail="invalid_lang_code")
    if payload.default_lang not in payload.enabled_langs:
        raise HTTPException(status_code=400, detail="default_not_enabled")
    async with _session(tenant_id) as session:
        meta = await session.get(TenantMeta, 1)
        if not meta:
            meta = TenantMeta(id=1)
            session.add(meta)
        meta.default_lang = payload.default_lang
        meta.enabled_langs = payload.enabled_langs
        await session.commit()
    return ok(
        {
            "default_lang": payload.default_lang,
            "enabled_langs": payload.enabled_langs,
        }
    )
