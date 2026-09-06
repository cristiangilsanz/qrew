# converts every exception every service can raise into a uniform json response
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
    HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorResponse,
        "description": "Validation error",
    },
    HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorResponse,
        "description": "Too many requests",
    },
    HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorResponse,
        "description": "Server error",
    },
}


# builds the uniform error body every handler returns
def _error_body(message: str, field: str | None = None) -> dict[str, Any]:
    return {"detail": {"message": message, "field": field}}


# converts an http exception into its json response
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
        body = _error_body(str(detail) if detail else "")
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers=getattr(exc, "headers", None),
    )


# converts a validation error location into a field name
def _location_to_field(loc: tuple[int | str, ...]) -> str | None:
    parts = [str(p) for p in loc[1:] if not isinstance(p, int)]
    return ".".join(parts) if parts else None


_PYDANTIC_VALUE_ERROR_PREFIX = "Value error, "


# renders a field name the way a person would read it back
def _humanise_field(field: str | None) -> str:
    if not field:
        return "Request"
    name = field.split(".")[-1].replace("_", " ").strip()
    return name[:1].upper() + name[1:] if name else "Request"


# describes a failed constraint in the same noun and verb shape as every other message
def _describe_violation(error_type: str, field: str | None) -> str:
    subject = _humanise_field(field)
    if error_type == "missing":
        return f"{subject} missing."
    if error_type in {"string_too_short", "too_short"}:
        return f"{subject} too short."
    if error_type in {"string_too_long", "too_long"}:
        return f"{subject} too long."
    if error_type in {
        "greater_than",
        "greater_than_equal",
        "less_than",
        "less_than_equal",
    }:
        return f"{subject} out of range."
    return f"{subject} rejected."


# keeps a validator's own wording and rewrites whatever pydantic phrased itself
def _validation_message(error_type: str, msg: str, field: str | None) -> str:
    if msg.startswith(_PYDANTIC_VALUE_ERROR_PREFIX):
        return msg[len(_PYDANTIC_VALUE_ERROR_PREFIX) :]
    return _describe_violation(error_type, field)


# converts a request validation error into its json response
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
    loc = first.get("loc", ())
    field = _location_to_field(tuple(loc))
    message = _validation_message(
        str(first.get("type", "")), str(first.get("msg", "")), field
    )
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_body(message, field),
    )


# converts a rate limit rejection into its json response
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content=_error_body(f"Rate limit exceeded: {exc.detail}"),
    )


# logs and converts an unexpected exception into a generic json response
async def _unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
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


# builds the standard invalid credentials response
def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail={"message": "Could not validate credentials", "field": None},
        headers={"WWW-Authenticate": "Bearer"},
    )


# registers every exception handler on the application
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unexpected_exception_handler)
