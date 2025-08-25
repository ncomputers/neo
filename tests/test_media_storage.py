import asyncio
import importlib
import sys
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from starlette.datastructures import UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _setup(tmp_path, monkeypatch):
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
    return client, storage


def _jpeg_with_exif():
    img = Image.new("RGB", (10, 10), color="red")
    exif = Image.Exif()
    exif[0x9003] = "2020:01:01 00:00:00"
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_upload_rejects_bad_type(tmp_path, monkeypatch):
    client, _ = _setup(tmp_path, monkeypatch)
    resp = client.post(
        "/api/outlet/t1/media/upload",
        files={"file": ("foo.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_upload_rejects_oversize(tmp_path, monkeypatch):
    client, _ = _setup(tmp_path, monkeypatch)
    big = b"x" * (2 * 1024 * 1024 + 1)
    resp = client.post(
        "/api/outlet/t1/media/upload",
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert resp.status_code == 413


def test_upload_strips_exif(tmp_path, monkeypatch):
    client, storage = _setup(tmp_path, monkeypatch)
    img_bytes = _jpeg_with_exif()
    resp = client.post(
        "/api/outlet/t1/media/upload",
        files={"file": ("img.jpg", img_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    key = resp.json()["data"]["key"]
    saved = storage.read(key)
    img = Image.open(BytesIO(saved))
    assert len(img.getexif()) == 0


def test_s3_presign(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "bkt")

    class DummyClient:
        def __init__(self):
            self.last = {}

        def generate_presigned_url(self, op, Params, ExpiresIn):
            self.last = {"op": op, "Params": Params, "ExpiresIn": ExpiresIn}
            return f"https://example.com/{op}/{Params['Key']}"

        def get_object(self, Bucket, Key):
            return {"Body": BytesIO(b"data")}

    import api.app.storage.s3_backend as s3_backend

    client = DummyClient()
    backend = s3_backend.S3Backend(client=client)
    upload = UploadFile(filename="foo.txt", file=BytesIO(b"x"), headers={"ETag": "abc"})
    url, key = asyncio.run(backend.save("t1", upload))
    assert client.last["Params"]["CacheControl"] == "public, max-age=86400"
    assert client.last["Params"]["Metadata"]["etag"] == "abc"
    assert url == f"https://example.com/put_object/{key}"
    get_url = backend.url(key)
    assert client.last["Params"]["ResponseCacheControl"] == "public, max-age=86400"
    assert get_url == f"https://example.com/get_object/{key}"
