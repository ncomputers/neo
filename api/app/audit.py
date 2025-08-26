# audit.py

"""Audit logging models and helpers.

This module defines simple SQLAlchemy models for a master and tenant audit
log. Helper functions allow application code to record events and purge old
records according to a retention policy configured during onboarding.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_settings

Base = declarative_base()


class AuditMaster(Base):
    """Audit log for master database events."""

    __tablename__ = "audit_master"

    id = Column(Integer, primary_key=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Audit(Base):
    """Audit log for tenant database events."""

    __tablename__ = "audit"

    id = Column(Integer, primary_key=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QrPackLog(Base):
    """Log entries for QR pack generation and reprints."""

    __tablename__ = "qr_pack_log"

    id = Column(Integer, primary_key=True)
    pack_id = Column(String, nullable=False)
    count = Column(Integer, nullable=False)
    requester = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Simple SQLite backing store for demonstration and tests.
engine = create_engine(
    "sqlite:///./audit.db", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def log_event(actor: str, action: str, entity: str, master: bool = False) -> None:
    """Persist an audit entry for ``actor`` performing ``action`` on ``entity``."""

    model = AuditMaster if master else Audit
    with SessionLocal() as session:
        session.add(model(actor=actor, action=action, entity=entity))
        session.commit()


def log_qr_pack(pack_id: str, count: int, requester: str, reason: str) -> None:
    """Persist a QR pack generation or reprint event."""

    with SessionLocal() as session:
        session.add(
            QrPackLog(
                pack_id=pack_id,
                count=count,
                requester=requester,
                reason=reason,
            )
        )
        session.commit()


def purge_old_logs(days: Optional[int] = None) -> int:
    """Delete audit rows older than ``days`` and return number purged.

    If ``days`` is omitted the retention period from :func:`config.get_settings`
    is used.
    """

    retention = days or get_settings().audit_retention_days
    cutoff = datetime.utcnow() - timedelta(days=retention)
    with SessionLocal() as session:
        removed = (
            session.query(AuditMaster).filter(AuditMaster.created_at < cutoff).delete()
            + session.query(Audit).filter(Audit.created_at < cutoff).delete()
        )
        session.commit()
    return removed


if __name__ == "__main__":  # pragma: no cover - manual invocation
    purge_old_logs()
