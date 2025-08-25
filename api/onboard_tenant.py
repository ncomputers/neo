# onboard_tenant.py

"""Helper utilities for provisioning a new tenant database.

The :func:`create_tenant` function creates a dedicated PostgreSQL database,
runs Alembic migrations and records basic tenant metadata in the master
database.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from config import get_settings
from app.models_master import Tenant


def create_tenant(
    name: str,
    domain: str,
    *,
    logo_url: str | None = None,
    primary_color: str | None = None,
    gst_mode: bool = False,
    inv_prefix: str | None = None,
    inv_reset: str = "never",
    ema_window: int | None = None,
    kds_sla_secs: int | None = None,
    license_limits: dict[str, int] | None = None,
) -> URL:
    """Provision a new tenant database and record its metadata.

    Parameters
    ----------
    name, domain:
        Basic tenant identifiers.
    logo_url, primary_color, gst_mode, inv_prefix, ema_window,
    kds_sla_secs, license_limits:
        Optional branding and configuration overrides stored alongside the
        tenant record. ``kds_sla_secs`` defines the time in seconds an order
        item may remain in ``IN_PROGRESS`` before triggering an alert.

    Returns
    -------
    URL
        SQLAlchemy URL for the newly created tenant database.

    Raises
    ------
    subprocess.CalledProcessError
        If Alembic migrations fail.
    """

    settings = get_settings()
    # Use AUTOCOMMIT so CREATE DATABASE can run outside a transaction
    master_engine = create_engine(
        settings.postgres_master_url, isolation_level="AUTOCOMMIT"
    )

    tenant_db_name = f"tenant_{uuid.uuid4().hex[:8]}"
    tenant_url = make_url(
        settings.postgres_tenant_dsn_template.format(tenant_id=tenant_db_name)
    )

    with master_engine.connect() as conn:
        # Create the isolated tenant database
        conn.execute(text(f'CREATE DATABASE "{tenant_db_name}"'))

    alembic_cfg = Path(__file__).with_name("alembic.ini")
    # Apply migrations so the new database has the latest schema
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
        # Persist tenant metadata in master DB
        tenant = Tenant(
            name=name,
            domain=domain,
            logo_url=logo_url,
            primary_color=primary_color,
            gst_mode=gst_mode,
            inv_prefix=inv_prefix,
            inv_reset=inv_reset,
            ema_window=ema_window,
            kds_sla_secs=kds_sla_secs,
            license_limits=license_limits or {},
        )
        session.add(tenant)
        session.commit()

    return tenant_url


__all__ = ["create_tenant"]
