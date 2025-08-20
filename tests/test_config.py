# test_config.py
"""Tests for configuration loading and overrides."""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import AcceptanceMode, get_settings


def setup_function(func):
    get_settings.cache_clear()


def test_defaults():
    settings = get_settings()
    assert settings.acceptance_mode is AcceptanceMode.ITEM


def test_environment_override(monkeypatch):
    monkeypatch.setenv("POSTGRES_MASTER_URL", "override")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.postgres_master_url == "override"
