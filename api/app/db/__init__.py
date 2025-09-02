from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.obs import add_query_logger

from ..models_master import Base as MasterBase
from ..models_tenant import Base as TenantBase

# Helpers to initialise an in-memory database for tests. These helpers are
# intentionally side-effect free; the returned session factory and engine are
# not exposed until tests explicitly assign them to module-level variables.


def create_test_session() -> tuple[sessionmaker, Engine]:
    """Return a session factory and engine for tests.

    The database uses an in-memory SQLite engine with a static pool so that
    multiple connections share the same data. Both master and tenant schemas
    are created to mirror the production setup.
    """

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    add_query_logger(engine, "test")
    MasterBase.metadata.create_all(bind=engine)
    TenantBase.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_factory, engine


# Placeholders to be populated by tests. Application code should import these
# names and, during tests, they will be initialised via ``create_test_session``
# from the respective ``conftest.py``.
SessionLocal: sessionmaker | None = None
engine: Engine | None = None

__all__ = ["SessionLocal", "engine", "create_test_session"]
