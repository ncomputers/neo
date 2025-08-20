from __future__ import annotations

"""Tenant database connection helpers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings

settings = get_settings()


def get_engine(tenant_id: str):
    """Return a database engine and session factory for ``tenant_id``."""
    url = settings.postgres_tenant_url.format(tenant_id=tenant_id)
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(url, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, SessionLocal

__all__ = ["get_engine"]
