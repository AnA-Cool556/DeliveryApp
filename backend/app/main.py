from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.errors import ApiError, api_error_handler, validation_error_handler
from app.orders import router as orders_router

app = FastAPI(title="DeliveryApp API", version="0.1.0")
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.include_router(orders_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
