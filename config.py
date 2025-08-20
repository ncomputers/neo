from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    postgres_master_url: str
    postgres_tenant_url: str
    redis_url: str
    minio_url: str
    proxy_url: str


@lru_cache
def get_settings() -> Settings:
    config_path = Path(__file__).with_name("config.json")
    data = json.loads(config_path.read_text())
    return Settings(**data)
