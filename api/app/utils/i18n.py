from __future__ import annotations

from typing import Dict, Optional


def get_text(
    field: Optional[str],
    lang: str,
    field_i18n: Optional[Dict[str, str]] = None,
    fallback: str = "en",
) -> str:
    """Return localized text from ``field_i18n`` with graceful fallbacks.

    Parameters
    ----------
    field:
        The default English value.
    lang:
        Desired language code.
    field_i18n:
        Optional mapping of language codes to translations.
    fallback:
        Fallback language code used when ``lang`` is unavailable.
    """
    if field_i18n:
        if lang in field_i18n and field_i18n[lang]:
            return field_i18n[lang]
        if fallback in field_i18n and field_i18n[fallback]:
            return field_i18n[fallback]
        if field:
            return field
        for value in field_i18n.values():
            if value:
                return value
    return field or ""
