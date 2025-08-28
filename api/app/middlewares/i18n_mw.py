from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class I18nMiddleware(BaseHTTPMiddleware):
    """Resolve request language from query, cookie, or default."""

    def __init__(self, app, cookie_name: str = "glang") -> None:
        super().__init__(app)
        self.cookie_name = cookie_name
        self.max_age = 60 * 60 * 24 * 180  # six months

    async def dispatch(self, request: Request, call_next):
        query_lang = request.query_params.get("lang")
        cookie_lang = request.cookies.get(self.cookie_name)
        default_lang = getattr(request.app.state, "default_lang", "en")
        enabled = getattr(request.app.state, "enabled_langs", ["en"])

        if query_lang and query_lang in enabled:
            lang = query_lang
        elif cookie_lang and cookie_lang in enabled:
            lang = cookie_lang
        else:
            lang = default_lang if default_lang in enabled else "en"

        request.state.lang = lang
        response = await call_next(request)
        response.set_cookie(self.cookie_name, lang, max_age=self.max_age)
        return response
