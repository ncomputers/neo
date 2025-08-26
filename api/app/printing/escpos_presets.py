"""Render ESC/POS templates for different paper sizes."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "escpos"
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)

TEMPLATE_MAP: Dict[str, str] = {
    "58mm": "58mm.txt",
    "80mm": "80mm.txt",
}


def render_preset(size: str, vars: Dict[str, Any]) -> str:
    """Render the ESC/POS template for ``size`` with ``vars``."""
    template_name = TEMPLATE_MAP.get(size)
    if template_name is None:
        raise KeyError(size)
    template = _env.get_template(template_name)
    return template.render(**vars)
