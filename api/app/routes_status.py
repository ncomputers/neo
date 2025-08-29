from __future__ import annotations

"""Public status page and dependency info."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/status/deps")
async def status_deps() -> dict:
    """Return status of third-party dependencies."""
    # Placeholder values; in real deployment these would check external webhooks
    return {"webhooks": {"payments": "ok"}}


@router.get("/status")
async def status_page() -> HTMLResponse:
    """Very small HTML status page."""
    html = """
    <html><head><title>Status</title></head>
    <body>
      <h1>Service Status</h1>
      <pre id=\"data\"></pre>
      <script>
        fetch('/status.json').then(r=>r.json()).then(d=>{
          document.getElementById('data').innerText = JSON.stringify(d, null, 2);
        });
      </script>
    </body></html>
    """
    return HTMLResponse(html)
