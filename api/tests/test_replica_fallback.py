import os
import pathlib
import sys
import asyncio
import uuid

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./dev_master.db")
os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)

import fakeredis.aioredis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from api.app.db import SessionLocal, replica  # noqa: E402
from api.app.models_tenant import (  # noqa: E402
    Category as CategoryModel,
    MenuItem as MenuItemModel,
)
from api.app.models_master import Base as MasterBase, Tenant  # noqa: E402
from api.app.models_tenant import Base as TenantBase  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.routes_metrics import db_replica_healthy  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def setup_module() -> None:
    app.state.redis = fakeredis.aioredis.FakeRedis()


def _setup_databases(tenant_id: str) -> None:
    async def setup_async() -> None:
        master_url = os.environ["DATABASE_URL"]
        master_engine = create_async_engine(master_url, future=True)
        async with master_engine.begin() as conn:
            await conn.run_sync(MasterBase.metadata.create_all)
            await conn.execute(Tenant.__table__.delete())
            await conn.execute(
                Tenant.__table__.insert().values(
                    id=uuid.UUID(hex=tenant_id),
                    name="Tenant",
                )
            )
        await master_engine.dispose()

        tenant_url = os.environ["POSTGRES_TENANT_DSN_TEMPLATE"].format(
            tenant_id=tenant_id
        )
        tenant_engine = create_async_engine(tenant_url, future=True)
        async with tenant_engine.begin() as conn:
            await conn.run_sync(TenantBase.metadata.create_all)
        await tenant_engine.dispose()

    asyncio.run(setup_async())


def test_replica_fallback_menu_and_charts() -> None:
    os.environ["READ_REPLICA_URL"] = "sqlite+aiosqlite:///./dev_replica.db"
    replica.READ_REPLICA_URL = os.environ["READ_REPLICA_URL"]
    replica._engine = None
    replica._sessionmaker = None
    replica._healthy = False

    tenant_id = uuid.uuid4().hex
    _setup_databases(tenant_id)

    with SessionLocal() as session:
        session.query(MenuItemModel).delete()
        session.query(CategoryModel).delete()
        session.commit()
        cat = CategoryModel(name="Snacks", sort=0)
        session.add(cat)
        session.flush()
        session.add(MenuItemModel(name="Cake", price=10, category_id=cat.id))
        session.commit()

    async def scenario() -> None:
        await replica.check_replica(app)
        assert db_replica_healthy._value.get() == 1
        assert client.get("/menu/items").status_code == 200

        orig_ping = replica._ping

        async def fail_ping(engine):
            raise Exception("boom")

        replica._ping = fail_ping  # type: ignore
        await replica.check_replica(app)
        assert db_replica_healthy._value.get() == 0

        async with replica.replica_session() as session:
            tenant = await session.get(Tenant, uuid.UUID(hex=tenant_id))
            assert tenant is not None

        menu_resp = client.get("/menu/items")
        assert menu_resp.status_code == 200

        replica._ping = orig_ping  # type: ignore
        await replica.check_replica(app)
        assert db_replica_healthy._value.get() == 1

    asyncio.run(scenario())
