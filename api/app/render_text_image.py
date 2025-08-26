from __future__ import annotations

import io
from typing import List

from PIL import Image, ImageDraw, ImageFont


def render_text_image(text: str) -> bytes:
    """Render ``text`` to a PNG image and return raw bytes."""
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    lines: List[str] = text.splitlines() or [""]
    bbox_a = font.getbbox("A")
    line_height = bbox_a[3] - bbox_a[1]
    max_width = 0
    for line in lines:
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        if line_width > max_width:
            max_width = line_width
    width = max_width + 10
    height = line_height * len(lines) + 10

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    y = 5
    for line in lines:
        draw.text((5, y), line, font=font, fill="black")
        y += line_height

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
