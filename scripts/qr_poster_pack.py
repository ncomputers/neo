"""Generate QR poster PDFs for tables."""

from __future__ import annotations

import argparse
import base64
from io import BytesIO
from zipfile import ZipFile

import qrcode

from api.app.pdf.render import render_template
from api.app.routes_onboarding import TENANTS

_BLANK_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PQIv5gAAAABJRU5ErkJggg=="


def _qr_data_url(url: str) -> str:
    try:
        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        b64 = _BLANK_PNG
    return f"data:image/png;base64,{b64}"


def generate_pack(tenant_id: str, size: str = "A4") -> bytes:
    tenant = TENANTS.get(tenant_id)
    if not tenant:
        raise ValueError("Tenant not found")

    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        for t in tenant.get("tables", []):
            url = f"https://example.com/{tenant_id}/{t['qr_token']}"
            qr = _qr_data_url(url)
            pdf_bytes, _ = render_template(
                "qrposter.html",
                {
                    "label": t.get("label", t["code"]),
                    "qr": qr,
                    "size": size,
                    "instructions": "Scan to order & pay",
                },
            )
            zf.writestr(f"{t['code']}.pdf", pdf_bytes)
    buffer.seek(0)
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate QR poster pack for an outlet")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--size", choices=["A4", "A5"], default="A4")
    parser.add_argument(
        "--output", default="poster_pack.zip", help="Output ZIP file path"
    )
    args = parser.parse_args()

    data = generate_pack(args.tenant, args.size)
    with open(args.output, "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
