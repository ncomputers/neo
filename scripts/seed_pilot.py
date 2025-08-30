#!/usr/bin/env python3
"""Seed a pilot tenant with demo data and helpers.

This utility prepares a demo tenant with a basic menu, ten tables and
mock configuration suitable for staging-to-pilot refreshes. It creates the
tenant database, runs migrations, seeds demo menu data and activates the
license for 30 days in mock UPI mode. QR posters are generated for the
allocated tables, sample orders and coupons are inserted, a referral code
is generated and basic staff PINs are created for owner, kitchen and
manager roles.

The script relies on environment variables used by other seeding helpers
(``POSTGRES_MASTER_URL`` and ``POSTGRES_TENANT_DSN_TEMPLATE``).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import subprocess
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure project root and ``api`` package are importable when invoked as a
# standalone script.
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from api.app.db.tenant import get_tenant_session  # noqa: E402
from api.app.db.master import get_session as get_master_session  # noqa: E402
from api.app.models_master import Tenant  # noqa: E402
from api.app.models_tenant import (
    Coupon,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Staff,
    Table,
)  # noqa: E402
from api.app.routes_onboarding import TENANTS  # noqa: E402
from api.app.billing import create_referral  # noqa: E402
from qr_poster_pack import generate_pack  # noqa: E402


async def _add_tables(session: AsyncSession) -> None:
    """Ensure ten tables exist in the tenant database."""
    result = await session.execute(select(Table))
    existing = len(result.scalars().all())
    for i in range(existing + 1, 11):
        session.add(
            Table(
                tenant_id=uuid.uuid4(),
                name=f"Table {i}",
                code=f"T-{i:03d}",
                qr_token=uuid.uuid4().hex,
            )
        )
    await session.commit()


def _pilot_staff() -> list[Staff]:
    """Return basic staff records with simple PINs."""
    pins = {
        "owner": "1111",
        "kitchen": "2222",
        "manager": "3333",
    }
    staff = []
    for role, pin in pins.items():
        staff.append(Staff(name=role.title(), role=role, pin_hash=pin))
    return staff


async def _create_staff(session: AsyncSession) -> None:
    session.add_all(_pilot_staff())
    await session.commit()


async def _create_coupons(session: AsyncSession) -> None:
    """Insert a couple of demo coupons."""
    session.add_all(
        [
            Coupon(code="WELCOME10", percent=10),
            Coupon(code="FLAT50", flat=50),
        ]
    )
    await session.commit()


async def _create_sample_orders(session: AsyncSession) -> None:
    """Create sample orders using existing menu items."""
    items = (await session.execute(select(MenuItem).limit(2))).scalars().all()
    tables = (await session.execute(select(Table.id).limit(2))).scalars().all()
    for table_id in tables:
        order = Order(
            table_id=table_id,
            status=OrderStatus.CONFIRMED,
            placed_at=dt.datetime.utcnow(),
        )
        session.add(order)
        await session.flush()
        for item in items:
            session.add(
                OrderItem(
                    order_id=order.id,
                    item_id=item.id,
                    name_snapshot=item.name,
                    price_snapshot=item.price,
                    qty=1,
                    status="SERVED",
                )
            )
    await session.commit()


def _create_referral_code(tenant_id: str) -> None:
    """Generate a referral code for the tenant and print it."""
    ref = create_referral(tenant_id)
    print(f"Referral code: {ref.code}")


async def _activate_license(tenant_id: str) -> None:
    """Mark tenant license active for 30 days and enable UPI mock mode."""
    async with get_master_session() as session:
        tenant = await session.get(Tenant, tenant_id)
        if tenant:
            tenant.subscription_expires_at = dt.datetime.utcnow() + dt.timedelta(
                days=30
            )
            limits = tenant.license_limits or {}
            limits["upi_mock"] = True
            tenant.license_limits = limits
            await session.commit()


async def _generate_qr_pack(tenant_id: str) -> None:
    """Render QR posters for the tenant's tables."""
    async with get_tenant_session(tenant_id) as session:
        rows = await session.execute(select(Table.code, Table.qr_token))
        tables = [{"code": code, "qr_token": token} for code, token in rows.all()]
    TENANTS[tenant_id] = {"tables": tables}
    data = generate_pack(tenant_id)
    Path(f"{tenant_id}_qr_pack.zip").write_bytes(data)


async def seed(tenant_id: str) -> None:
    subprocess.run(
        ["python", "scripts/tenant_create_db.py", "--tenant", tenant_id], check=True
    )
    subprocess.run(
        ["python", "scripts/tenant_migrate.py", "--tenant", tenant_id], check=True
    )
    subprocess.run(
        ["python", "scripts/demo_seed.py", "--tenant", tenant_id, "--reset"], check=True
    )

    async with get_tenant_session(tenant_id) as session:
        await _add_tables(session)
        await _create_staff(session)
        await _create_coupons(session)
        await _create_sample_orders(session)

    await _activate_license(tenant_id)
    await _generate_qr_pack(tenant_id)
    _create_referral_code(tenant_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed pilot tenant with demo data")
    parser.add_argument("--tenant", default="pilot", help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(seed(args.tenant))


if __name__ == "__main__":
    main()
