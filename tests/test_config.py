# test_config.py
import json
import pathlib
import sys
from pathlib import Path

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from config import AcceptanceMode, get_settings


def _settings():
    get_settings.cache_clear()
    return get_settings()


def test_defaults_from_config():
    settings = _settings()
    assert (
        settings.redis_url == json.loads(Path("config.json").read_text())["redis_url"]
    )


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://override")
    settings = _settings()
    assert settings.redis_url == "redis://override"
    monkeypatch.delenv("REDIS_URL")


def test_missing_key_uses_default(monkeypatch):
    original = Path("config.json").read_text()
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self: json.dumps(
            {k: v for k, v in json.loads(original).items() if k != "acceptance_mode"}
        ),
    )
    settings = _settings()
    assert settings.acceptance_mode == AcceptanceMode.ITEM
