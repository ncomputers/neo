from __future__ import annotations

"""Utility helpers for Noto font downloads."""

from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT_DIR = Path(__file__).resolve().parents[3]
FONTS_DIR = ROOT_DIR / "static" / "fonts"

_FONT_URLS = {
    "NotoSans-Regular.ttf": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
    "NotoSans-Bold.ttf": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf",
    "NotoSansDevanagari-Regular.ttf": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    "NotoSansDevanagari-Bold.ttf": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
    "NotoSansGujarati-Regular.ttf": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansGujarati/NotoSansGujarati-Regular.ttf",
    "NotoSansGujarati-Bold.ttf": "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansGujarati/NotoSansGujarati-Bold.ttf",
}


def _download_https(url: str, path: Path) -> None:
    """Download ``url`` to ``path`` ensuring HTTPS only."""
    u = urlparse(url)
    if u.scheme != "https":
        raise ValueError("Only https URLs are allowed")
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(resp.content)


def ensure_fonts() -> None:
    """Download required fonts if missing."""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in _FONT_URLS.items():
        path = FONTS_DIR / filename
        if not path.exists():
            _download_https(url, path)
