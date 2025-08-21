from __future__ import annotations

"""Notification enqueueing service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from ..db.tenant import get_engine
from ..models_tenant import AlertRule, NotificationOutbox


async def enqueue(tenant_id: str, event: str, payload: dict) -> None:
    """Queue notifications for ``event`` based on enabled rules."""

    try:
        engine = get_engine(tenant_id)
    except Exception:  # pragma: no cover - missing DSN config
        return
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with Session() as session:
            try:
                rules = await session.scalars(
                    select(AlertRule).where(
                        AlertRule.event == event, AlertRule.enabled.is_(True)
                    )
                )
            except SQLAlchemyError:
                await session.rollback()
                return
            for rule in rules.all():
                session.add(
                    NotificationOutbox(
                        event=event,
                        payload=payload,
                        channel=rule.channel,
                        target=rule.target,
                    )
                )
            await session.commit()
    finally:
        await engine.dispose()


__all__ = ["enqueue"]
