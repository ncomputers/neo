"""Abstraction layer for video streaming backends."""

from __future__ import annotations

import subprocess
from typing import List

from config import get_settings


def get_backend() -> str:
    """Return the configured video backend.

    GStreamer is used when ``USE_GSTREAMER`` is enabled in settings; otherwise
    FFmpeg is selected.
    """

    return "gstreamer" if get_settings().use_gstreamer else "ffmpeg"


def build_command(source: str, destination: str) -> List[str]:
    """Return the shell command for streaming ``source`` to ``destination``."""

    if get_backend() == "gstreamer":
        return ["gst-launch-1.0", source, destination]
    return ["ffmpeg", "-i", source, destination]


def stream_video(source: str, destination: str) -> subprocess.CompletedProcess:
    """Stream video from ``source`` to ``destination`` using the chosen backend."""

    cmd = build_command(source, destination)
    return subprocess.run(cmd, check=True)


__all__ = ["get_backend", "build_command", "stream_video"]
