"""SQLAlchemy-backed repository implementations.

This module now also exposes ``TenantGuard``, a tiny mixin providing
assertion helpers to ensure that repository helpers are always scoped to a
specific tenant.  The guard verifies that the active SQLAlchemy session is
bound to the expected tenant database.  It is deliberately lightweight and
raises ``PermissionError`` when a mismatch is detected.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class TenantGuard:
    """Utility mixin providing tenant scoping assertions."""

    @staticmethod
    def assert_tenant(session: AsyncSession, tenant_id: str) -> None:
        """Ensure ``session`` is bound to the database for ``tenant_id``.

        Parameters
        ----------
        session:
            Active SQLAlchemy session.
        tenant_id:
            Identifier expected to be present in the session's database URL.

        Raises
        ------
        AssertionError
            If ``tenant_id`` is blank.
        PermissionError
            If the session appears to be bound to a different tenant's
            database.
        """

        if not tenant_id:
            raise AssertionError("tenant_id required")

        bind = session.bind
        db_name = getattr(getattr(bind, "url", None), "database", "") if bind else ""
        if tenant_id not in (db_name or ""):
            raise PermissionError("tenant mismatch")


__all__ = ["TenantGuard"]

