from fastapi import FastAPI

from .menu import router as menu_router

app = FastAPI()
app.include_router(menu_router, prefix="/menu")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
