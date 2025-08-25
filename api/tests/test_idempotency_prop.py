import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import main as app_main  # noqa: E402
from api.app import routes_guest_order  # noqa: E402
from api.app.deps.tenant import get_tenant_id as header_tenant_id  # noqa: E402
from api.app.main import app  # noqa: E402
from api.app.repos_sqlalchemy import orders_repo_sql  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    """Return a test client with in-memory redis and dummy tenant session."""
    app.state.redis = fakeredis.aioredis.FakeRedis()
    original_guard = app_main.subscription_guard

    async def _pass_through(request, call_next):
        return await call_next(request)

    app_main.subscription_guard = _pass_through

    async def _fake_get_tenant_session():
        class _DummySession:
            pass

        return _DummySession()

    app.dependency_overrides[routes_guest_order.get_tenant_id] = header_tenant_id
    app.dependency_overrides[
        routes_guest_order.get_tenant_session
    ] = _fake_get_tenant_session

    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()
    app_main.subscription_guard = original_guard


# strategy for a list of order items
item_ids = st.text(
    st.characters(min_codepoint=48, max_codepoint=57), min_size=1, max_size=3
)
qtys = st.integers(min_value=1, max_value=5)
items_strategy = st.lists(
    st.fixed_dictionaries({"item_id": item_ids, "qty": qtys}),
    min_size=1,
    max_size=5,
)

key_strategy = st.uuids().map(lambda u: u.hex)


@given(items=items_strategy, key=key_strategy)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_idempotent_order_single_creation(client, items, key, monkeypatch):
    """Posting the same order twice with identical Idempotency-Key only creates once."""
    calls = 0

    # reset redis for each example to avoid cross-test caching
    client.app.state.redis = fakeredis.aioredis.FakeRedis()

    async def _fake_create_order(session, table_token, lines):
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(orders_repo_sql, "create_order", _fake_create_order)

    headers = {"X-Tenant-ID": "demo", "Idempotency-Key": key}
    payload = {"items": items}

    resp1 = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp1.status_code == 200

    resp2 = client.post("/g/T-001/order", headers=headers, json=payload)
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert calls == 1
