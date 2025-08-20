# Tenant Alembic Environment

This directory contains the Alembic environment used for tenant-specific database migrations. It expects an asynchronous SQLAlchemy engine to be provided at runtime via `config.attributes["engine"]`.

## Programmatic usage

```python
import asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://user:pass@host/db"

engine = create_async_engine(DB_URL)
cfg = Config()
cfg.set_main_option("script_location", "api/alembic_tenant")
cfg.set_main_option("sqlalchemy.url", DB_URL)
cfg.attributes["engine"] = engine

command.upgrade(cfg, "head")
asyncio.run(engine.dispose())
```

The environment also supports offline migrations by setting `sqlalchemy.url` and running standard Alembic commands.
