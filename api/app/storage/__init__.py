"""Storage backend selector.

Provides a unified interface to save media and fetch public URLs using either a
local filesystem or S3-backed implementation. The backend is chosen via the
``STORAGE_BACKEND`` environment variable (``local`` by default).
"""

from __future__ import annotations

import os
from typing import Protocol, Tuple
from fastapi import UploadFile


class StorageBackend(Protocol):
    """Minimal protocol implemented by storage backends."""

    async def save(self, tenant: str, file: UploadFile) -> Tuple[str, str]:
        """Persist ``file`` for ``tenant`` and return ``(url, key)``."""

    def read(self, key: str) -> bytes:
        """Return raw bytes for ``key``."""

    def url(self, key: str) -> str:
        """Return a public URL for ``key``."""


backend = os.getenv("STORAGE_BACKEND", "local").lower()

if backend == "s3":  # pragma: no cover - exercised via tests
    from .s3_backend import S3Backend as _Backend
else:
    from .local_backend import LocalBackend as _Backend

# Expose a singleton instance used across the application
storage: StorageBackend = _Backend()

__all__ = ["storage", "StorageBackend"]
