# routes_admin_backup.py
"""Admin route to trigger tenant backups."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

from .utils.responses import ok

router = APIRouter()


@router.post("/api/outlet/{tenant_id}/backup")
async def backup_tenant(tenant_id: str) -> dict:
    """Create a JSON backup for ``tenant_id`` and return the file path."""

    root = Path(__file__).resolve().parents[2]
    scripts_dir = root / "scripts"
    backups_dir = root / "backups"
    backups_dir.mkdir(exist_ok=True)
    out_file = backups_dir / f"{tenant_id}.json"
    cmd = [
        sys.executable,
        str(scripts_dir / "tenant_backup.py"),
        "--tenant",
        tenant_id,
        "--out",
        str(out_file),
    ]
    await asyncio.to_thread(subprocess.run, cmd, check=True)
    return ok({"path": str(out_file)})
