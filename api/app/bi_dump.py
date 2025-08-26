from __future__ import annotations

"""Helpers for BI parquet dumps."""

from datetime import date
from typing import Iterable


def build_manifest(day: date, files: Iterable[dict]) -> dict:
    """Return a manifest document for ``day`` and ``files``.

    Parameters
    ----------
    day:
        Date the dump represents.
    files:
        Iterable of mapping objects each containing ``dataset`` and ``s3_key``.
    """

    return {"date": day.isoformat(), "files": list(files)}
