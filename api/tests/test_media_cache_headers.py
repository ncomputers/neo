import asyncio
import importlib
import pathlib
import sys
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile
from starlette.staticfiles import StaticFiles

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


class CacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response


def test_local_media_cache_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))

    import api.app.storage as storage_module

    importlib.reload(storage_module)
    backend = storage_module.storage

    sample = UploadFile(filename="hello.txt", file=BytesIO(b"hi"))
    url, key = asyncio.run(backend.save("t1", sample))

    app = FastAPI()
    app.mount("/media", CacheStaticFiles(directory=str(tmp_path)))
    client = TestClient(app)

    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "public, max-age=86400"
    assert resp.headers.get("etag")


def test_s3_presigned_cache_headers(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "bkt")

    class DummyClient:
        def __init__(self):
            self.last = {}

        def generate_presigned_url(self, op, Params, ExpiresIn):
            self.last = {"op": op, "Params": Params, "ExpiresIn": ExpiresIn}
            query = "&".join(f"{k}={v}" for k, v in Params.items() if k not in {"Bucket", "Key"})
            return f"https://example.com/{op}/{Params['Key']}?{query}"

        def get_object(self, Bucket, Key):
            return {"Body": BytesIO(b"data")}

        def head_object(self, Bucket, Key):
            return {"Metadata": {"etag": "abc"}, "ETag": '"abc"'}

    import api.app.storage.s3_backend as s3_backend

    backend = s3_backend.S3Backend(client=DummyClient())
    upload = UploadFile(filename="foo.txt", file=BytesIO(b"x"), headers={"ETag": "abc"})
    url, key = asyncio.run(backend.save("t1", upload))

    get_url, etag = backend.url(key)
    params = parse_qs(urlparse(get_url).query)
    cc = params.get("ResponseCacheControl", [""])[0]
    assert "public" in cc
    assert int(cc.split("max-age=")[1]) >= 86400
    assert etag == "abc"
