import uvicorn

from com.qode.qrew.v1.identity.settings import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.identity.main:app",
        reload=settings.debug,
        host=settings.host,
        port=settings.port,
    )
