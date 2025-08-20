# qr.py

"""Utility helpers to generate static QR codes for tables."""

from __future__ import annotations

from pathlib import Path

import qrcode


def generate_table_qr(
    table_id: str, base_url: str, output_dir: str = "static/qr"
) -> str:
    """Generate a PNG QR code for a table and return the file path.

    Parameters
    ----------
    table_id:
        Identifier for the table. Used for both the encoded URL and the
        output filename.
    base_url:
        Base URL of the tenant application. The table identifier will be
        appended to create the encoded link.
    output_dir:
        Directory where the QR code image will be stored. The directory is
        created if it does not already exist.
    """

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    target_url = f"{base_url}/tables/{table_id}"
    img = qrcode.make(target_url)
    file_path = Path(output_dir) / f"{table_id}.png"
    img.save(file_path)
    return str(file_path)
