from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..models_master import Base as MasterBase
from ..models_tenant import Base as TenantBase

# Shared database engine and session factory for the application.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
MasterBase.metadata.create_all(bind=engine)
TenantBase.metadata.create_all(bind=engine)

__all__ = ["SessionLocal", "engine"]
