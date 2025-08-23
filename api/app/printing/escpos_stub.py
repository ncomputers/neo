"""Minimal helpers to compose ESC/POS tickets.

This is a very small subset of the command set sufficient for tests and
experimental printing in labs.  It avoids external dependencies and keeps a
simple in-memory buffer which can be converted to bytes for sending to a
printer.
"""

from __future__ import annotations

from typing import List

_buffer: List[bytes] = []


def header(text: str) -> None:
    """Add a centred header line.

    The buffer is initialised (ESC @) so the first byte is always ESC.
    """

    _buffer.clear()
    _buffer.append(b"\x1b@")  # Initialize printer
    # Double height and width
    _buffer.append(b"\x1b!\x38")
    _buffer.append(text.encode("ascii", errors="ignore"))
    _buffer.append(b"\n")
    _buffer.append(b"\x1b!\x00")  # Reset


def line(item: str, qty: int) -> None:
    """Add a simple item line."""

    _buffer.append(f"{item} x{qty}\n".encode("ascii", errors="ignore"))


def cut() -> None:
    """Append a full cut command."""

    _buffer.append(b"\n\x1dV\x00")


def to_bytes() -> bytes:
    """Return ticket bytes and reset buffer."""

    data = b"".join(_buffer)
    _buffer.clear()
    return data
