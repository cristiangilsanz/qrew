# exposes the shared exception handlers and error schemas
from .handlers import (
    ErrorDetail,
    ErrorResponse,
    credentials_exception,
    default_responses,
    register_exception_handlers,
)

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "credentials_exception",
    "default_responses",
    "register_exception_handlers",
]
