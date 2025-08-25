from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List
from uuid import UUID
import secrets

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .models_tenant import ApiKey
from .utils.responses import ok

router = APIRouter()

DEFAULT_SCOPES = ["read:reports", "read:menu", "write:orders"]


@asynccontextmanager
async def _session(tenant_id: str):
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.post("/api/outlet/{tenant_id}/api-keys")
async def create_api_key(tenant_id: str) -> dict:
    token = secrets.token_hex(16)
    record = ApiKey(token=token, scopes=DEFAULT_SCOPES)
    async with _session(tenant_id) as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return ok({"id": record.id, "token": token, "scopes": record.scopes})


@router.get("/api/outlet/{tenant_id}/api-keys")
async def list_api_keys(tenant_id: str) -> dict:
    async with _session(tenant_id) as session:
        result = await session.execute(select(ApiKey))
        keys: List[ApiKey] = result.scalars().all()
    payload = [{"id": k.id, "token": k.token, "scopes": k.scopes} for k in keys]
    return ok(payload)


@router.get("/api/outlet/{tenant_id}/api-keys/{key_id}")
async def get_api_key(tenant_id: str, key_id: UUID) -> dict:
    async with _session(tenant_id) as session:
        key = await session.get(ApiKey, key_id)
        if key is None:
            raise HTTPException(status_code=404, detail="not found")
    return ok({"id": key.id, "token": key.token, "scopes": key.scopes})


@router.delete("/api/outlet/{tenant_id}/api-keys/{key_id}")
async def delete_api_key(tenant_id: str, key_id: UUID) -> dict:
    async with _session(tenant_id) as session:
        key = await session.get(ApiKey, key_id)
        if key is None:
            raise HTTPException(status_code=404, detail="not found")
        await session.delete(key)
        await session.commit()
    return ok(None)
