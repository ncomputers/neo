import json
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.app.main import app  # noqa: E402
from api.app.middlewares.logging import LoggingMiddleware  # noqa: E402


def test_log_line_has_request_id(caplog):
    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="api"):
        client.get("/health")
    line = caplog.messages[0]
    data = json.loads(line)
    assert data["request_id"]


def _make_app():
    test_app = FastAPI()
    test_app.add_middleware(LoggingMiddleware)

    @test_app.post("/echo")
    async def echo(data: dict):
        return data

    @test_app.post("/g/fail")
    async def fail():
        return JSONResponse({}, status_code=400)

    return test_app


def test_body_redaction(caplog):
    client = TestClient(_make_app())
    with caplog.at_level(logging.INFO, logger="api"):
        client.post("/echo", json={"pin": "1234"})
    inbound = json.loads(caplog.messages[0])
    assert inbound["body"]["pin"] == "***"


def test_guest_4xx_sampling(monkeypatch, caplog):
    monkeypatch.setattr("api.app.middlewares.logging.LOG_SAMPLE_GUEST_4XX", 0.5)
    client = TestClient(_make_app())
    monkeypatch.setattr("api.app.middlewares.logging.random.random", lambda: 0.9)
    with caplog.at_level(logging.INFO, logger="api"):
        client.post("/g/fail")
    assert len(caplog.messages) == 0

    caplog.clear()
    monkeypatch.setattr("api.app.middlewares.logging.random.random", lambda: 0.1)
    with caplog.at_level(logging.INFO, logger="api"):
        client.post("/g/fail")
    assert len(caplog.messages) == 2
