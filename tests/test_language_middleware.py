from fastapi import FastAPI, Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from api.app.middlewares.language import LanguageMiddleware


def create_app():
    app = FastAPI()
    app.state.default_lang = "en"
    app.state.enabled_langs = ["en", "hi"]

    @app.get("/")
    async def root(request: Request):
        return PlainTextResponse(request.state.lang)

    app.add_middleware(LanguageMiddleware)
    return app


def test_query_overrides_cookie():
    app = create_app()
    client = TestClient(app)
    client.cookies.set("lang", "hi")
    resp = client.get("/?lang=en")
    assert resp.text == "en"
    assert resp.cookies["lang"] == "en"


def test_cookie_used_when_no_query():
    app = create_app()
    client = TestClient(app)
    client.cookies.set("lang", "hi")
    resp = client.get("/")
    assert resp.text == "hi"


def test_default_when_no_cookie_or_query():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.text == "en"
