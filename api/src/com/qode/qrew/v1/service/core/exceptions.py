import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
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
    app.add_exception_handler(Exception, _unhandled_exception_handler)
