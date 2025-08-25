import pathlib
import sys

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))  # noqa: E402

from api.app import main as app_main  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.main import app  # noqa: E402

app.state.redis = fakeredis.aioredis.FakeRedis()


class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture(scope="module", autouse=True)
def _setup_teardown():
    original_guard = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()
    yield
    app_main.subscription_guard = original_guard
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_menu_import_dryrun_good() -> None:
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/outlet/demo/menu/import/dryrun",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("menu.csv", b"name,price\nPizza,10\n", "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["errors"] == []


@pytest.mark.anyio
async def test_menu_import_dryrun_bad() -> None:
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/outlet/demo/menu/import/dryrun",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("menu.csv", b"title,amount\nPizza,10\n", "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["errors"]
