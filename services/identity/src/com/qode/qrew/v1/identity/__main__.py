import uvicorn

from com.qode.qrew.v1.identity.core.config import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.identity.app:app",
        reload=settings.debug,
        host=settings.host,
        port=settings.port,
    )
