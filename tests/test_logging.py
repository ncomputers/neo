import json
import logging
import random
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.app.middlewares.logging import LoggingMiddleware  # noqa: E402
from api.app.middlewares.request_id import RequestIdMiddleware  # noqa: E402
from api.app.obs.logging import JsonFormatter  # noqa: E402


def test_request_id_propagation(monkeypatch, caplog):
    monkeypatch.setattr("api.app.middlewares.logging.LOG_SAMPLE_2XX", 1)
    client = TestClient(_make_app())
    with caplog.at_level(logging.INFO, logger="api"):
        resp = client.get("/health", headers={"X-Request-ID": "abc"})
    assert resp.headers["X-Request-ID"] == "abc"
    line = caplog.messages[1]
    data = json.loads(line)
    assert data["req_id"] == "abc"


def test_request_id_generation(monkeypatch, caplog):
    monkeypatch.setattr("api.app.middlewares.logging.LOG_SAMPLE_2XX", 1)
    client = TestClient(_make_app())
    with caplog.at_level(logging.INFO, logger="api"):
        resp = client.get("/health")
    rid = resp.headers["X-Request-ID"]
    assert rid
    data = json.loads(caplog.messages[1])
    assert data["req_id"] == rid


def _make_app():
    test_app = FastAPI()
    test_app.add_middleware(RequestIdMiddleware)
    test_app.add_middleware(LoggingMiddleware)

    @test_app.get("/health")
    async def health():
        return {"ok": True}

    @test_app.post("/echo")
    async def echo(data: dict):
        return data

    @test_app.post("/g/fail")
    async def fail():
        return JSONResponse({}, status_code=400)

    return test_app


def test_body_redaction(monkeypatch, caplog):
    monkeypatch.setattr("api.app.middlewares.logging.LOG_SAMPLE_2XX", 1)
    client = TestClient(_make_app())
    payload = {
        "pin": "1234",
        "utr": "u",
        "auth": "a",
        "gstin": "g",
        "email": "e@example.com",
        "nested": {"email": "n@example.com"},
    }
    params = {"auth": "q", "email": "q@example.com"}
    with caplog.at_level(logging.INFO, logger="api"):
        client.post("/echo", json=payload, params=params)
    inbound = json.loads(caplog.messages[0])
    body = inbound["body"]
    query = inbound["query"]
    for k in ["pin", "utr", "auth", "gstin", "email"]:
        assert body[k] == "***"
    assert body["nested"]["email"] == "***"
    assert query["auth"] == "***"
    assert query["email"] == "***"


def test_guest_4xx_sampling(monkeypatch, caplog):
    monkeypatch.setattr("api.app.middlewares.logging.LOG_SAMPLE_2XX", 1)
    monkeypatch.setattr("api.app.middlewares.logging.LOG_SAMPLE_GUEST_4XX", 0.1)
    random.seed(1)
    client = TestClient(_make_app())
    with caplog.at_level(logging.INFO, logger="api"):
        for _ in range(100):
            client.post("/g/fail")
    logged = len(caplog.messages) // 2
    assert 5 <= logged <= 15


def test_2xx_sampling(monkeypatch, caplog):
    monkeypatch.setattr("api.app.middlewares.logging.LOG_SAMPLE_2XX", 0.1)
    random.seed(1)
    client = TestClient(_make_app())
    with caplog.at_level(logging.INFO, logger="api"):
        for _ in range(100):
            client.get("/health")
    logged = len(caplog.messages) // 2
    assert 5 <= logged <= 15


def test_json_logger_redaction():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        "api",
        logging.INFO,
        __file__,
        0,
        "call 9998887776 email foo@example.com utr 1234567890",
        (),
        None,
    )
    data = json.loads(formatter.format(record))
    msg = data["msg"]
    assert "9998887776" not in msg
    assert "foo@example.com" not in msg
    assert "1234567890" not in msg
    assert msg.count("***") >= 3
