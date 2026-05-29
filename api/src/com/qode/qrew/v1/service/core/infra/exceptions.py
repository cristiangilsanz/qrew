import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logger = structlog.get_logger(__name__)


async def _unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Convert any unhandled exception into a generic error response."""
    await logger.aexception(
        "unhandled_exception",
        method=request.method,
        url=str(request.url),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach error handlers to the application."""
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unexpected_exception_handler)
