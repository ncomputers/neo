from __future__ import annotations

"""Utility helpers for Noto font downloads."""

from pathlib import Path
from urllib.request import urlretrieve

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


def ensure_fonts() -> None:
    """Download required fonts if missing."""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in _FONT_URLS.items():
        path = FONTS_DIR / filename
        if not path.exists():
            urlretrieve(url, path)
