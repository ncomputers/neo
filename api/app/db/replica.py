from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.app.obs import add_query_logger

from . import master

READ_REPLICA_URL = os.getenv("READ_REPLICA_URL")

_engine: AsyncEngine | None = None
_sessionmaker: sessionmaker[AsyncSession] | None = None


async def _ping(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


def _init_replica() -> None:
    global _engine, _sessionmaker
    if not READ_REPLICA_URL:
        return
    engine = create_async_engine(READ_REPLICA_URL, future=True)
    add_query_logger(engine, "replica")
    try:
        asyncio.run(_ping(engine))
    except Exception:
        return
    _engine = engine
    _sessionmaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


_init_replica()


@asynccontextmanager
async def replica_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a replica session, falling back to primary."""
    if _sessionmaker is None:
        async with master.get_session() as session:
            yield session
        return
    session = _sessionmaker()
    try:
        yield session
    finally:
        await session.close()


def read_only(func):
    """Placeholder decorator for marking read-only endpoints."""
    return func


__all__ = ["replica_session", "read_only"]
