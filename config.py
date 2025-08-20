# config.py
"""Load application settings combining ``config.json`` and environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from enum import Enum
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class AcceptanceMode(str, Enum):
    """Modes for accepting orders with item-level as default."""

    ITEM = "item"
    ORDER = "order"


class Settings(BaseSettings):
    """Application configuration read from environment variables and JSON."""

    model_config = SettingsConfigDict(env_file=".env")

    postgres_master_url: str
    postgres_tenant_url: str
    redis_url: str
    minio_url: str
    proxy_url: str
    acceptance_mode: AcceptanceMode = AcceptanceMode.ITEM
    ema_window: int = 10
    sla_sound_alert: bool = False
    sla_color_alert: bool = False
    hide_out_of_stock_items: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return ``Settings`` merging ``config.json`` with environment overrides."""

    config_path = Path(__file__).with_name("config.json")
    data = json.loads(config_path.read_text())
    for key in list(data):
        env_key = key.upper()
        if env_key in os.environ:
            data[key] = os.environ[env_key]
    return Settings(**data)
