from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.app.obs import add_query_logger
from api.app.routes_metrics import db_replica_healthy

from . import master

READ_REPLICA_URL = os.getenv("READ_REPLICA_URL")

_engine: AsyncEngine | None = None
_sessionmaker: sessionmaker[AsyncSession] | None = None
_healthy = False


async def _ping(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def check_replica(app: FastAPI) -> None:
    """Verify replica health and update state/metrics."""
    global _engine, _sessionmaker, _healthy
    healthy = False
    if READ_REPLICA_URL:
        engine = _engine or create_async_engine(READ_REPLICA_URL, future=True)
        try:
            await _ping(engine)
        except Exception:
            await engine.dispose()
            _engine = None
            _sessionmaker = None
        else:
            if _engine is None:
                add_query_logger(engine, "replica")
                _engine = engine
            _sessionmaker = sessionmaker(
                _engine, expire_on_commit=False, class_=AsyncSession
            )
            healthy = True
    _healthy = healthy
    app.state.replica_healthy = healthy
    db_replica_healthy.set(1 if healthy else 0)


async def monitor(app: FastAPI) -> None:
    """Background task for periodic replica health checks."""
    while True:
        await check_replica(app)
        await asyncio.sleep(30)


@asynccontextmanager
async def replica_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a replica session, falling back to primary."""
    if _sessionmaker is None or not _healthy:
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


__all__ = ["replica_session", "read_only", "monitor", "check_replica"]
