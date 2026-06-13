from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

logger = structlog.get_logger(__name__)


class ErrorDetail(BaseModel):
    message: str = Field(..., description="Human-readable explanation of the failure.")
    field: str | None = Field(default=None)


class ErrorResponse(BaseModel):
    detail: ErrorDetail


default_responses: dict[int | str, dict[str, Any]] = {
    HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Bad request"},
    HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
    HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
    HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not found"},
    HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Conflict"},
    HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Validation error"},
    HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Too many requests"},
    HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Server error"},
}


def _error_body(message: str, field: str | None = None) -> dict[str, Any]:
    return {"detail": {"message": message, "field": field}}


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    detail: Any = exc.detail
    body: dict[str, Any]
    if isinstance(detail, dict) and "message" in detail:
        message = str(detail.get("message", ""))  # type: ignore[arg-type]
        field_raw = detail.get("field")  # type: ignore[arg-type]
        field_str = str(field_raw) if isinstance(field_raw, str) else None
        body = _error_body(message, field_str)
    else:
        body = _error_body(str(detail) if detail else "")  # pyright: ignore[reportUnknownArgumentType]
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers=getattr(exc, "headers", None),
    )


def _location_to_field(loc: tuple[int | str, ...]) -> str | None:
    parts = [str(p) for p in loc[1:] if not isinstance(p, int)]
    return ".".join(parts) if parts else None


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del request
    errors = exc.errors()
    if not errors:
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body("Validation error"),
        )
    first = errors[0]
    message = str(first.get("msg", "Validation error"))
    loc = first.get("loc", ())
    field = _location_to_field(tuple(loc))
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_body(message, field),
    )


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content=_error_body(f"Rate limit exceeded: {exc.detail}"),
    )


async def _unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    await logger.aexception(
        "unhandled_exception",
        method=request.method,
        url=str(request.url),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("Internal server error"),
    )


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail={"message": "Could not validate credentials", "field": None},
        headers={"WWW-Authenticate": "Bearer"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unexpected_exception_handler)
