from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.routes.order import router as order_router
from .payments.errors import PaymentProviderError

app = FastAPI(
    title="RailSwitch",
    version="0.1.0",
)

app.include_router(order_router)


@app.exception_handler(PaymentProviderError)
async def payment_provider_error_handler(
    _: Request, error: PaymentProviderError
) -> JSONResponse:
    return JSONResponse(
        status_code=error.http_status_code,
        content={"detail": error.public_detail()},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
