from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.app.obs import add_query_logger

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("POSTGRES_MASTER_URL", "sqlite+aiosqlite:///./dev_master.db"),
)

_engine: AsyncEngine | None = None
_sessionmaker: sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return a singleton async engine for the master database."""
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, future=True)
        add_query_logger(_engine, "master")
        _sessionmaker = sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
    return _engine


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session and ensure it is closed afterwards."""
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None  # for type checkers
    session = _sessionmaker()
    try:
        yield session
    finally:
        await session.close()


__all__ = ["get_engine", "get_session"]
