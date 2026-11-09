"""Domain exceptions and their HTTP mappings."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base error for predictable business failures."""

    status_code = 400
    code = "app_error"

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class ProductUnavailableError(AppError):
    status_code = 409
    code = "product_unavailable"


class OrderStateError(AppError):
    status_code = 409
    code = "order_state_error"


class PaymentError(AppError):
    status_code = 502
    code = "payment_error"


class ProviderError(PaymentError):
    pass


class WebhookSignatureError(AppError):
    status_code = 400
    code = "invalid_webhook_signature"


class OutOfStock(AppError):
    status_code = 409
    code = "out_of_stock"


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
