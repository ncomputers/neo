from __future__ import annotations

"""Guest consent capture endpoint."""

from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .deps.tenant import get_tenant_id
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter(prefix="/g")


class ConsentPayload(BaseModel):
    phone: str | None = None
    allow_analytics: bool = False
    allow_wa: bool = False


async def get_tenant_session(
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        yield session


@router.post("/consent")
@audit("guest_consent", {"phone"})
async def save_consent(
    payload: ConsentPayload,
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    if payload.phone:
        res = await session.execute(
            text(
                "UPDATE customers SET allow_analytics=:a, allow_wa=:w WHERE phone=:p"
            ),
            {"a": payload.allow_analytics, "w": payload.allow_wa, "p": payload.phone},
        )
        if res.rowcount == 0:
            await session.execute(
                text(
                    "INSERT INTO customers (name, phone, allow_analytics, allow_wa) VALUES ('', :p, :a, :w)"
                ),
                {"p": payload.phone, "a": payload.allow_analytics, "w": payload.allow_wa},
            )
        await session.commit()
    return ok({})


__all__ = ["router"]
