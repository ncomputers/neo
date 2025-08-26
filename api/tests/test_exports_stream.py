"""Tests streaming CSV export and SSE progress."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app import db as app_db  # noqa: E402

sys.modules.setdefault("db", app_db)  # noqa: E402
from api.app import models_tenant, routes_exports  # noqa: E402
from api.app.db.tenant import get_engine  # noqa: E402
from api.app.models_tenant import Invoice  # noqa: E402

os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///./tenant_{tenant_id}.db"
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def tenant_session() -> AsyncSession:
    tenant_id = "demo"
    engine = get_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(models_tenant.Base.metadata.create_all)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        if engine.url.get_backend_name().startswith("sqlite"):
            await engine.dispose()
            db_path = engine.url.database
            if db_path and db_path != ":memory:" and os.path.exists(db_path):
                os.remove(db_path)
        else:
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
            await engine.dispose()


app = FastAPI()
app.include_router(routes_exports.router)
app.state.redis = fakeredis.aioredis.FakeRedis()


@pytest.fixture
async def seeded_session(tenant_session):
    invoices = [
        Invoice(
            order_group_id=i,
            number=f"INV{i}",
            bill_json={"subtotal": 0, "tax_breakup": {}, "total": 0},
            tip=0,
            total=0,
        )
        for i in range(3000)
    ]
    tenant_session.add_all(invoices)
    await tenant_session.commit()
    return tenant_session


@pytest.fixture
async def seeded_session_many(tenant_session):
    rows = [
        {
            "order_group_id": i,
            "number": f"INV{i}",
            "bill_json": {"subtotal": 0, "tax_breakup": {}, "total": 0},
            "tip": 0,
            "total": 0,
        }
        for i in range(11000)
    ]
    await tenant_session.execute(Invoice.__table__.insert(), rows)
    await tenant_session.commit()
    return tenant_session


@pytest.mark.anyio
async def test_stream_chunks(seeded_session, monkeypatch):
    monkeypatch.setattr(routes_exports, "DEFAULT_LIMIT", 5000)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET", "/api/outlet/demo/exports/invoices.csv?limit=2500&chunk_size=500"
        ) as resp:
            assert resp.status_code == 200
            await resp.aread()
        data = await client.get(
            "/api/outlet/demo/exports/invoices.csv?limit=2500&chunk_size=500"
        )
        rows = list(csv.reader(io.StringIO(data.text)))
    assert len(rows) - 1 == 2500


@pytest.mark.anyio
async def test_cap_hint(seeded_session, monkeypatch):
    monkeypatch.setattr(routes_exports, "ABSOLUTE_MAX_ROWS", 100)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET", "/api/outlet/demo/exports/invoices.csv?limit=200"
        ) as resp:
            chunks = [chunk async for chunk in resp.aiter_bytes()]
    data = b"".join(chunks).decode().splitlines()
    assert len(data) == 102  # header + 100 rows + hint
    assert data[-1].endswith("cap hit")


@pytest.mark.anyio
async def test_sse_progress():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def produce():
            await app.state.redis.set("export:job1:progress", 0)
            await asyncio.sleep(0.05)
            await app.state.redis.set("export:job1:progress", 1000)
            await asyncio.sleep(0.05)
            await app.state.redis.set("export:job1:progress", 2000)
            await asyncio.sleep(0.2)
            await app.state.redis.delete("export:job1:progress")

        async def consume():
            async with client.stream(
                "GET", "/api/outlet/demo/exports/invoices/progress/job1"
            ) as sse_resp:
                events = []
                event_type = None
                async for line in sse_resp.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        continue
                    if line.startswith("data:"):
                        if event_type == "progress":
                            events.append(json.loads(line[5:]))
                        elif event_type == "complete":
                            events.append("complete")
                            break
                return events

        prod = asyncio.create_task(produce())
        events = await consume()
        await prod
    assert events == [{"count": 1000}, {"count": 2000}, "complete"]


@pytest.mark.anyio
async def test_streaming_progress_over_10k(seeded_session_many, monkeypatch):
    orig_sleep = asyncio.sleep

    async def fast_sleep(_):
        await orig_sleep(0)

    monkeypatch.setattr(routes_exports.asyncio, "sleep", fast_sleep)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def consume():
            async with client.stream(
                "GET", "/api/outlet/demo/exports/invoices/progress/bigjob"
            ) as sse_resp:
                events = []
                event_type = None
                async for line in sse_resp.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        continue
                    if line.startswith("data:"):
                        if event_type == "progress":
                            events.append(json.loads(line[5:])["count"])
                        elif event_type == "complete":
                            events.append("complete")
                            break
                return events

        consume_task = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        async with client.stream(
            "GET", "/api/outlet/demo/exports/invoices.csv?limit=10500&job=bigjob"
        ) as resp:
            assert resp.status_code == 200
            assert (
                resp.headers.get("Transfer-Encoding") == "chunked"
                or resp.headers.get("Content-Length") is None
            )
            await resp.aread()
        events = await consume_task
    assert events == list(range(1000, 10001, 1000)) + ["complete"]
