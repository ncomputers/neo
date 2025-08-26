"""Utilities for streaming CSV responses."""

from __future__ import annotations

import asyncio
import csv
import io
from typing import Any, AsyncIterable, AsyncIterator, Iterable


class CSVStream:
    """Asynchronous iterator producing CSV byte chunks."""

    def __init__(
        self, rows_iterable: AsyncIterable[Iterable[Any]], flush_size: int = 1000
    ):
        self.rows_iterable = rows_iterable
        self.flush_size = flush_size
        self.buffer = io.StringIO()
        self.writer = csv.writer(self.buffer)
        self.rows_written = 0

    def write_row(self, row: Iterable[Any]) -> bytes | None:
        """Append a row and return bytes if a flush occurred."""
        self.writer.writerow(row)
        self.rows_written += 1
        if self.rows_written >= self.flush_size:
            data = self.buffer.getvalue().encode("utf-8")
            self.buffer.seek(0)
            self.buffer.truncate(0)
            self.rows_written = 0
            return data
        return None

    async def _gen(self) -> AsyncIterator[bytes]:
        async for row in self.rows_iterable:
            chunk = self.write_row(row)
            if chunk:
                yield chunk
                await asyncio.sleep(0)
        tail = self.buffer.getvalue().encode("utf-8")
        if tail:
            yield tail

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._gen()


def csv_stream(
    rows_iterable: AsyncIterable[Iterable[Any]], flush_size: int = 1000
) -> CSVStream:
    """Create a :class:`CSVStream` for the given rows."""
    return CSVStream(rows_iterable, flush_size)


def stream_csv(
    headers: Iterable[Any],
    row_iter: AsyncIterable[Iterable[Any]],
    chunk_size: int = 1000,
) -> CSVStream:
    """Return a CSV stream with ``headers`` prepended."""
    iterator = csv_stream(row_iter, flush_size=chunk_size)
    iterator.write_row(headers)
    return iterator

