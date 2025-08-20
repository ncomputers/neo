from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from pydantic import BaseSettings

class Settings(BaseSettings):
    postgres_master_url: str
    postgres_tenant_url: str
    redis_url: str
    minio_url: str
    proxy_url: str

    class Config:
        env_file = ".env"

    @classmethod
    def customise_sources(cls, init_settings, env_settings, file_secret_settings):
        return env_settings, cls.json_config_settings, init_settings, file_secret_settings

    @classmethod
    def json_config_settings(cls, settings):
        config_path = Path(__file__).with_name("config.json")
        return json.loads(config_path.read_text())

@lru_cache
def get_settings() -> Settings:
    return Settings()
