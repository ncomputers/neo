"""Invoice PDF rendering utilities."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Literal, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape()
)

_TEMPLATE_MAP = {
    "80mm": "invoice_80mm.html",
    "A4": "invoice_a4.html",
}


def render_template(
    template_name: str, context: dict, nonce: Optional[str] = None
) -> Tuple[bytes, str]:
    """Render ``context`` using ``template_name`` to PDF or HTML."""

    template = _env.get_template(template_name)
    if nonce:
        context = {**context, "csp_nonce": nonce}
    html = template.render(**context)
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf_bytes = weasyprint.HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        return pdf_bytes, "application/pdf"
    except Exception:
        return html.encode("utf-8"), "text/html"


def render_invoice(
    invoice_json: dict,
    size: Literal["80mm", "A4"] = "80mm",
    nonce: Optional[str] = None,
) -> Tuple[bytes, str]:
    """Render ``invoice_json`` to PDF or HTML.

    If WeasyPrint is installed, a PDF is returned with ``application/pdf``
    mimetype. Otherwise, the rendered HTML bytes are returned with
    ``text/html`` mimetype.
    """
    template_name = _TEMPLATE_MAP.get(size, _TEMPLATE_MAP["80mm"])
    template = _env.get_template(template_name)
    html = template.render(invoice=invoice_json, csp_nonce=nonce)
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf_bytes = weasyprint.HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        return pdf_bytes, "application/pdf"
    except Exception:
        return html.encode("utf-8"), "text/html"
