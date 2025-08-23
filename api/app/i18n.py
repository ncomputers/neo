from __future__ import annotations

"""Simple i18n helpers for guest-facing strings."""

from typing import Dict

GUEST_CATALOG: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "labels": {
            "menu": "Menu",
            "order": "Order",
            "pay": "Pay",
            "get_bill": "Get Bill",
        },
        "errors": {
            "TABLE_LOCKED": "Table not ready",
            "FEATURE_OFF": "Feature disabled",
        },
    },
    "hi": {
        "labels": {
            "menu": "मेनू",
            "order": "ऑर्डर करें",
            "pay": "भुगतान करें",
            "get_bill": "बिल प्राप्त करें",
        },
        "errors": {
            "TABLE_LOCKED": "टेबल तैयार नहीं है",
            "FEATURE_OFF": "फ़ीचर बंद है",
        },
    },
}


def select_language(accept_language: str | None) -> str:
    """Pick the best supported language from the header."""

    if not accept_language:
        return "en"
    lang = accept_language.split(",")[0].split("-")[0].lower()
    return lang if lang in GUEST_CATALOG else "en"


def get_catalog(lang: str) -> Dict[str, Dict[str, str]]:
    """Return catalog for ``lang`` with English fallback."""

    return GUEST_CATALOG.get(lang, GUEST_CATALOG["en"])

