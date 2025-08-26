from __future__ import annotations

"""Utilities for streaming CSV rows."""

import csv
from io import StringIO
from typing import Iterable, Iterator, Sequence, Any


def stream_rows(rows: Iterable[Sequence[Any]], header: Sequence[Any] | None = None) -> Iterator[str]:
    """Yield CSV ``rows`` flushing buffer after every write.

    Parameters
    ----------
    rows:
        Iterable yielding row sequences.
    header:
        Optional header row to prepend.
    """
    buffer = StringIO()
    writer = csv.writer(buffer)
    if header:
        writer.writerow(list(header))
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
    for row in rows:
        writer.writerow(list(row))
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
