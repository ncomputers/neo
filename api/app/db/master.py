from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("POSTGRES_MASTER_URL", "sqlite+aiosqlite:///./dev_master.db")
READ_REPLICA_URL = os.getenv("READ_REPLICA_URL")

_engine: AsyncEngine | None = None
_sessionmaker: sessionmaker[AsyncSession] | None = None
_read_engine: AsyncEngine | None = None
_read_sessionmaker: sessionmaker[AsyncSession] | None = None


async def _ping(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


def _init_read_replica() -> None:
    global _read_engine, _read_sessionmaker
    if not READ_REPLICA_URL:
        return
    engine = create_async_engine(READ_REPLICA_URL, future=True)
    try:
        asyncio.run(_ping(engine))
    except Exception:
        return
    _read_engine = engine
    _read_sessionmaker = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )


_init_read_replica()


def get_engine() -> AsyncEngine:
    """Return a singleton async engine for the master database."""
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, future=True)
        _sessionmaker = sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
    return _engine


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session and ensure it is closed afterwards."""
    global _sessionmaker
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None  # for type checkers
    session = _sessionmaker()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def get_read_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a replica session, falling back to primary if unavailable."""
    global _read_sessionmaker
    if _read_sessionmaker is None:
        async with get_session() as session:
            yield session
        return
    session = _read_sessionmaker()
    try:
        yield session
    finally:
        await session.close()


__all__ = ["get_engine", "get_session", "get_read_session"]
