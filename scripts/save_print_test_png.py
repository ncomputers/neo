from __future__ import annotations

import argparse

import fakeredis.aioredis
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.render_text_image import render_text_image
from api.app.routes_print_test import router


def main() -> None:
    parser = argparse.ArgumentParser(description="Save print-test preview as PNG")
    parser.add_argument(
        "--printer", choices=["58mm", "80mm"], default="80mm", help="Printer width"
    )
    parser.add_argument("--output", default="print-test.png", help="Output PNG path")
    parser.add_argument("--url", default="", help="Base URL for remote API")
    args = parser.parse_args()
    if args.url:
        resp = requests.post(
            f"{args.url.rstrip('/')}/admin/print/test",
            json={"printer": args.printer},
            timeout=10,
        )
    else:
        fake = fakeredis.aioredis.FakeRedis()
        app = FastAPI()
        app.include_router(router)
        app.state.redis = fake
        client = TestClient(app)
        resp = client.post("/admin/print/test", json={"printer": args.printer})
    resp.raise_for_status()
    preview = resp.json()["preview"]
    image_bytes = render_text_image(preview)
    with open(args.output, "wb") as fh:
        fh.write(image_bytes)


if __name__ == "__main__":
    main()
