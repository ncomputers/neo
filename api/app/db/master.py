from __future__ import annotations

"""Master database connection utilities."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings
from .. import models

settings = get_settings()
connect_args: dict = {}
if settings.postgres_master_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
engine = create_engine(settings.postgres_master_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Create tables automatically when using SQLite for tests
if engine.url.get_backend_name() == "sqlite":
    models.Base.metadata.create_all(bind=engine)

__all__ = ["engine", "SessionLocal"]
