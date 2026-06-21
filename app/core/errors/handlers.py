from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors.base import AppError

# Advisory retry hint on 503 responses — not a measured queue depth or backpressure
# value; just a safe default so clients know when to try again.
_RETRY_AFTER_SECONDS = 30


def register_exception_handlers(app):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        body: dict = {"error_code": exc.error_code, "message": exc.message}
        if exc.detail is not None:
            body["detail"] = exc.detail
        if exc.status_code == 503:
            body["retry_after_seconds"] = _RETRY_AFTER_SECONDS
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        validation_errors = []
        for error in exc.errors():
            loc = error.get("loc", ())
            field = ".".join(str(x) for x in loc if x != "body")
            validation_errors.append({
                "field": field or None,
                "issue": error.get("msg"),
                "value": error.get("input"),
            })
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "validation_errors": validation_errors,
            },
        )
