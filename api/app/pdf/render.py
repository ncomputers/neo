"""Invoice PDF rendering utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Tuple
import importlib

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape()
)

_TEMPLATE_MAP = {
    "80mm": "invoice_80mm.html",
    "A4": "invoice_a4.html",
}

_KOT_TEMPLATE_MAP = {
    "80mm": "kot_80mm.html",
}


def render_invoice(
    invoice_json: dict, size: Literal["80mm", "A4"] = "80mm"
) -> Tuple[bytes, str]:
    """Render ``invoice_json`` to PDF or HTML.

    If WeasyPrint is installed, a PDF is returned with ``application/pdf``
    mimetype. Otherwise, the rendered HTML bytes are returned with
    ``text/html`` mimetype.
    """
    template_name = _TEMPLATE_MAP.get(size, _TEMPLATE_MAP["80mm"])
    template = _env.get_template(template_name)
    html = template.render(invoice=invoice_json)
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        return pdf_bytes, "application/pdf"
    except Exception:
        return html.encode("utf-8"), "text/html"


def render_kot(kot_json: dict, size: Literal["80mm"] = "80mm") -> Tuple[bytes, str]:
    """Render ``kot_json`` to PDF or HTML.

    Falls back to HTML when a PDF engine such as WeasyPrint is unavailable.
    """
    template_name = _KOT_TEMPLATE_MAP.get(size, _KOT_TEMPLATE_MAP["80mm"])
    template = _env.get_template(template_name)
    html = template.render(kot=kot_json)
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        return pdf_bytes, "application/pdf"
    except Exception:
        return html.encode("utf-8"), "text/html"
