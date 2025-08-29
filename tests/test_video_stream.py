import importlib

import config
from api.app.utils import video_stream


def _reload_settings():
    config.get_settings.cache_clear()
    importlib.reload(video_stream)


def test_ffmpeg_backend(monkeypatch):
    monkeypatch.delenv("USE_GSTREAMER", raising=False)
    _reload_settings()
    assert video_stream.get_backend() == "ffmpeg"
    assert video_stream.build_command("in", "out")[0] == "ffmpeg"


def test_gstreamer_backend(monkeypatch):
    monkeypatch.setenv("USE_GSTREAMER", "1")
    _reload_settings()
    assert video_stream.get_backend() == "gstreamer"
    assert video_stream.build_command("in", "out")[0] == "gst-launch-1.0"
