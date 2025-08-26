#!/usr/bin/env python3
"""Fetch Noto fonts used for PDF rendering."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from api.app.pdf.fonts import ensure_fonts

if __name__ == "__main__":
    ensure_fonts()
