from __future__ import annotations

import base64

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_print_test import router


def main() -> None:
    fake = fakeredis.aioredis.FakeRedis()
    app = FastAPI()
    app.include_router(router)
    app.state.redis = fake
    client = TestClient(app)

    resp = client.post("/admin/print/test", json={"printer": "80mm"})
    resp.raise_for_status()
    data = resp.json()
    image_bytes = base64.b64decode(data["image"])
    with open("print-test.png", "wb") as fh:
        fh.write(image_bytes)


if __name__ == "__main__":
    main()
