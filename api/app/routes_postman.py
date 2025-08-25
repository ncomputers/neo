from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

ROOT = Path(__file__).resolve().parent.parent.parent
COLLECTION_PATH = ROOT / "docs" / "postman_collection.json"
SCRIPT_PATH = ROOT / "scripts" / "gen_postman.py"


@router.get("/postman/collection.json")
def postman_collection() -> FileResponse:
    if not COLLECTION_PATH.exists():
        subprocess.run([sys.executable, str(SCRIPT_PATH)], check=True)
    return FileResponse(COLLECTION_PATH)
