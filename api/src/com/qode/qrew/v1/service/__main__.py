import uvicorn

from com.qode.qrew.v1.service.settings import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.service.main:app",
        reload=True,
        host=settings.host,
        port=settings.port,
    )
