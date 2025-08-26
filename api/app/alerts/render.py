"""Utility functions to render notification templates."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates"
_email_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR / "email"),
    autoescape=select_autoescape(["html", "xml"]),
)
_text_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR / "message"),
    autoescape=False,  # nosec B701: plain-text templates
)


def render_email(template: str, vars: Dict[str, str], subject_tpl: str) -> Tuple[str, str]:
    """Render an email subject and HTML body.

    Parameters:
        template: Template filename under ``templates/email``.
        vars: Variables available to the templates.
        subject_tpl: Jinja template string for the email subject.
    Returns:
        Tuple of rendered subject and HTML body.
    """
    subject = Environment(autoescape=True).from_string(subject_tpl).render(**vars)
    body = _email_env.get_template(template).render(**vars)
    return subject, body


def render_message(template: str, vars: Dict[str, str]) -> str:
    """Render a plain text message using ``template`` under ``templates/message``."""
    return _text_env.get_template(template).render(**vars)
