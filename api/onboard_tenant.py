"""Utilities for onboarding new tenants.

The :func:`create_tenant` helper provisions a new tenant database, applies the
current Alembic migrations and records tenant metadata in the master database.
This script is intended for internal staff use during the onboarding process.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from config import get_settings
from app.models import Tenant


def create_tenant(
    name: str,
    domain: str,
    *,
    logo_url: str | None = None,
    primary_color: str | None = None,
    gst_mode: bool = False,
    invoice_prefix: str | None = None,
    ema_window: int | None = None,
    license_limits: dict[str, int] | None = None,
) -> URL:
    """Provision a new tenant database and record its metadata.

    Returns the SQLAlchemy :class:`~sqlalchemy.engine.URL` for the new tenant
    database. The function assumes the configured master user has privileges to
    create databases and that Alembic is available on the PATH.
    """

    settings = get_settings()
    master_engine = create_engine(
        settings.postgres_master_url, isolation_level="AUTOCOMMIT"
    )

    tenant_db_name = f"tenant_{uuid.uuid4().hex[:8]}"
    tenant_url = make_url(settings.postgres_tenant_url).set(database=tenant_db_name)

    with master_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{tenant_db_name}"'))

    alembic_cfg = Path(__file__).with_name("alembic.ini")
    subprocess.run(
        [
            "alembic",
            "-c",
            str(alembic_cfg),
            "-x",
            f"db_url={tenant_url}",
            "upgrade",
            "head",
        ],
        check=True,
    )

    with Session(master_engine) as session:
        tenant = Tenant(
            name=name,
            domain=domain,
            logo_url=logo_url,
            primary_color=primary_color,
            gst_mode=gst_mode,
            invoice_prefix=invoice_prefix,
            ema_window=ema_window,
            license_limits=license_limits or {},
        )
        session.add(tenant)
        session.commit()

    return tenant_url


__all__ = ["create_tenant"]
