from pathlib import Path

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.app.routes_legal import router as legal_router

app = FastAPI()
app.include_router(legal_router)


def test_legal_pages_served():
    client = TestClient(app)
    pages = {
        "terms": "Terms of Service",
        "privacy": "Privacy Policy",
        "refund": "Cancellation & Refund Policy",
        "contact": "Contact Us",
    }
    for page, title in pages.items():
        resp = client.get(f"/legal/{page}")
        assert resp.status_code == 200
        assert title in resp.text


def test_invoice_templates_link_legal_pages():
    root = Path(__file__).resolve().parents[1]
    templates = ["templates/invoice_a4.html", "templates/invoice_80mm.html"]
    for template in templates:
        html = (root / template).read_text(encoding="utf-8")
        for path in ["terms", "privacy", "refund", "contact"]:
            assert f"/legal/{path}" in html
