"""CORS configuration derived from environment variables."""

from __future__ import annotations

import os

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
