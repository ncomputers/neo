import asyncio
from io import BytesIO
import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_local_backend_round_trip(tmp_path, monkeypatch):
    # Ensure local backend and temp directory
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))

    import api.app.auth as auth
    monkeypatch.setattr(auth, "role_required", lambda *roles: lambda: object())

    import api.app.storage as storage_module
    importlib.reload(storage_module)
    storage = storage_module.storage

    import api.app.routes_media as routes_media
    importlib.reload(routes_media)

    app = FastAPI()
    app.include_router(routes_media.router)
    client = TestClient(app)

    resp = client.post(
        "/api/outlet/t1/media/upload",
        files={"file": ("foo.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    key = data["key"]
    url = data["url"]
    assert url.endswith(key)
    assert storage.read(key) == b"hello"
    assert storage.url(key) == url


def test_s3_presign(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "bkt")

    class DummyClient:
        def generate_presigned_url(self, op, Params, ExpiresIn):
            return f"https://example.com/{op}/{Params['Key']}"

        def get_object(self, Bucket, Key):
            return {"Body": BytesIO(b"data")}

    import api.app.storage.s3_backend as s3_backend

    backend = s3_backend.S3Backend(client=DummyClient())
    upload = UploadFile(filename="foo.txt", file=BytesIO(b"x"))
    url, key = asyncio.run(backend.save("t1", upload))
    assert url == f"https://example.com/put_object/{key}"
    get_url = backend.url(key)
    assert get_url == f"https://example.com/get_object/{key}"
