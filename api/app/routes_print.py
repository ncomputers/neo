from fastapi import APIRouter, HTTPException, Response

from .printing import escpos_stub

router = APIRouter(prefix="/api/outlet/{tenant}/print")


@router.get("/test")
def print_test(tenant: str, size: str = "80mm") -> Response:
    if size != "80mm":  # pragma: no cover - simple guard
        raise HTTPException(status_code=400, detail="unsupported size")

    escpos_stub.header("Sample Ticket")
    escpos_stub.line("Coffee", 1)
    escpos_stub.cut()
    data = escpos_stub.to_bytes()
    return Response(content=data, media_type="application/octet-stream")
