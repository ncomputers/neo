"""Filesystem-based storage backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple
from uuid import uuid4

from fastapi import UploadFile


class LocalBackend:
    """Save media files under ``MEDIA_DIR`` and serve them from ``/media``."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or os.getenv("MEDIA_DIR", "media"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, tenant: str, file: UploadFile) -> Tuple[str, str]:
        key = f"{tenant}/{uuid4().hex}_{file.filename}"
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        contents = await file.read()
        path.write_bytes(contents)
        return self.url(key), key

    def read(self, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()

    def url(self, key: str) -> str:
        return f"/media/{key}"
