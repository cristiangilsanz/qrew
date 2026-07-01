import uvicorn

from com.qode.qrew.v1.catalog.core.config import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.catalog.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
