from fastapi import FastAPI

from app.api.routes.payment import router as payment_router

app = FastAPI(
    title="RailSwitch",
    version="0.1.0",
)

app.include_router(payment_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
