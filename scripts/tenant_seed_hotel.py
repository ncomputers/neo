#!/usr/bin/env python3
"""Create demo hotel rooms for a tenant.

This CLI seeds two rooms with predefined codes (``R-101`` and ``R-102``)
into the specified tenant database. Each room is assigned a unique QR token
and the identifiers are printed as JSON so developers can use them for local
smoke tests.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db.tenant import get_tenant_session
from api.app.models_tenant import Room


async def seed_rooms(session: AsyncSession) -> list[dict[str, int | str]]:
    """Insert two demo rooms and return their identifiers."""

    rooms: list[Room] = []
    for code in ("R-101", "R-102"):
        room = Room(code=code, qr_token=uuid.uuid4().hex)
        session.add(room)
        rooms.append(room)

    await session.flush()
    await session.commit()

    return [{"id": r.id, "code": r.code, "qr_token": r.qr_token} for r in rooms]


async def main(tenant_id: str) -> None:
    async with get_tenant_session(tenant_id) as session:
        rooms = await seed_rooms(session)
    print(json.dumps({"rooms": rooms}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo hotel rooms")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    asyncio.run(main(args.tenant))
