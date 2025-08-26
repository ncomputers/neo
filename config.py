# config.py

"""Application configuration utilities.

Values are primarily loaded from ``config.json`` and may be overridden by
environment variables. The :func:`get_settings` helper merges the two sources
and caches the result.
"""

from __future__ import annotations

import json
import os
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AcceptanceMode(str, Enum):
    """Determine when an order line is accepted.

    ``ITEM`` means each item can be accepted individually, whereas ``ORDER``
    requires the entire order to be accepted or rejected as a whole. The
    default application setting is ``ITEM``.
    """

    ITEM = "item"
    ORDER = "order"


class Settings(BaseSettings):
    """Application settings merged from JSON and environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_master_url: str = "sqlite+aiosqlite:///./dev_master.db"
    postgres_tenant_dsn_template: str = "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
    postgres_super_url: str | None = None
    redis_url: str
    minio_url: str
    proxy_url: str
    acceptance_mode: AcceptanceMode = AcceptanceMode.ITEM
    ema_window: int = 10
    kds_sla_secs: int = 900
    sla_sound_alert: bool = False
    sla_color_alert: bool = False
    hide_out_of_stock_items: bool = True
    audit_retention_days: int = 30
    happy_hour_windows: list[dict] = []
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    max_conn_per_ip: int = 20
    ab_tests_enabled: bool = False


# Cached singleton to avoid repeated file reads
@lru_cache
def get_settings() -> Settings:
    """Return merged settings with environment variable precedence.

    The configuration is read from ``config.json`` located alongside this file
    and fed into :class:`Settings`. Environment variables override any values
    from the JSON file. The result is cached to prevent repeated disk reads.
    """

    config_path = Path(__file__).with_name("config.json")
    data = json.loads(config_path.read_text())
    env_override = {
        k.lower(): v
        for k, v in os.environ.items()
        if k.lower() in Settings.model_fields
    }
    merged = {**data, **env_override}
    # Environment variables override values from the JSON file.
    return Settings(**merged)
