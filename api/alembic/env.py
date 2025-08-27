from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR.parent))

from app.db import MasterBase, TenantBase  # type: ignore  # noqa: E402

from config import get_settings  # type: ignore  # noqa: E402
from app import models_master  # type: ignore  # noqa: E402


config = context.config
fileConfig(config.config_file_name)

settings = get_settings()
DB_URLS = {
    "master": settings.postgres_master_url,
    "tenant": settings.postgres_tenant_dsn_template.format(tenant_id="tenant"),
}

target_metadata = models_master.Base.metadata



def _get_url() -> str:
    x_args = context.get_x_argument(as_dictionary=True)
    if "db_url" in x_args:
        return x_args["db_url"]
    return DB_URLS[x_args.get("db", "master")]


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = {"sqlalchemy.url": _get_url()}
    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
