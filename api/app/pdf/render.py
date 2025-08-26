"""Invoice PDF rendering utilities."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Literal, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape
from .fonts import FONTS_DIR, ensure_fonts

ROOT_DIR = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = ROOT_DIR / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape()
)

_TEMPLATE_MAP = {
    "80mm": "invoice_80mm.html",
    "A4": "invoice_a4.html",
}


def _register_fonts(font_config) -> None:
    """Download and register Noto fonts for INR and Indic glyphs."""

    ensure_fonts()
    fonts = [
        ("Noto Sans", "NotoSans-Regular.ttf", "400"),
        ("Noto Sans", "NotoSans-Bold.ttf", "700"),
        (
            "Noto Sans Devanagari",
            "NotoSansDevanagari-Regular.ttf",
            "400",
        ),
        (
            "Noto Sans Devanagari",
            "NotoSansDevanagari-Bold.ttf",
            "700",
        ),
        (
            "Noto Sans Gujarati",
            "NotoSansGujarati-Regular.ttf",
            "400",
        ),
        (
            "Noto Sans Gujarati",
            "NotoSansGujarati-Bold.ttf",
            "700",
        ),
    ]
    for family, filename, weight in fonts:
        path = FONTS_DIR / filename
        if path.exists():
            font_config.add_font_face(
                {
                    "src": [("external", path.as_uri())],
                    "font_family": family,
                    "font_style": "normal",
                    "font_weight": weight,
                    "font_stretch": "normal",
                },
                None,
            )


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
        font_config = weasyprint.text.fonts.FontConfiguration()
        _register_fonts(font_config)
        pdf_bytes = weasyprint.HTML(string=html, base_url=str(ROOT_DIR)).write_pdf(
            font_config=font_config
        )
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
        font_config = weasyprint.text.fonts.FontConfiguration()
        _register_fonts(font_config)
        pdf_bytes = weasyprint.HTML(string=html, base_url=str(ROOT_DIR)).write_pdf(
            font_config=font_config
        )
        return pdf_bytes, "application/pdf"
    except Exception:
        return html.encode("utf-8"), "text/html"
