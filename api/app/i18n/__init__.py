from __future__ import annotations

"""Guest message catalogs and helpers for localization."""

import json
from importlib import resources
from typing import Any, Dict

_DEFAULT_LANG = "en"
_SUPPORTED_LANGS = {"en", "hi", "gu"}
_catalog_cache: Dict[str, Dict[str, Any]] = {}


def _load_catalog(lang: str) -> Dict[str, Any]:
    try:
        with resources.open_text(__name__, f"{lang}.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        with resources.open_text(
            __name__, f"{_DEFAULT_LANG}.json", encoding="utf-8"
        ) as f:
            return json.load(f)


def get_catalog(lang: str) -> Dict[str, Any]:
    """Return the catalog for ``lang`` with caching and English fallback."""
    if lang not in _catalog_cache:
        _catalog_cache[lang] = _load_catalog(lang)
    return _catalog_cache[lang]


def get_msg(lang: str, key: str, **vars: Any) -> str:
    """Fetch a localized message by dotted ``key`` with optional formatting."""
    parts = key.split(".")
    msg: Any = get_catalog(lang)
    for part in parts:
        msg = msg.get(part) if isinstance(msg, dict) else None
        if msg is None:
            msg = get_catalog(_DEFAULT_LANG)
            for p in parts:
                msg = msg.get(p) if isinstance(msg, dict) else None
            break
    if isinstance(msg, str):
        return msg.format(**vars) if vars else msg
    return ""


def resolve_lang(accept_language: str | None, tenant_default: str | None = None) -> str:
    """Pick the best supported language from headers or tenant default."""
    if accept_language:
        prefs = []
        for idx, part in enumerate(accept_language.split(",")):
            part = part.strip()
            if not part:
                continue
            token = part.split(";")
            lang = token[0].split("-")[0].lower()
            q = 1.0
            if len(token) > 1 and token[1].strip().startswith("q="):
                try:
                    q = float(token[1].strip()[2:])
                except ValueError:
                    q = 0.0
            prefs.append((-q, idx, lang))
        for _, _, lang in sorted(prefs):
            if lang in _SUPPORTED_LANGS:
                return lang
    if tenant_default and tenant_default in _SUPPORTED_LANGS:
        return tenant_default
    return _DEFAULT_LANG
