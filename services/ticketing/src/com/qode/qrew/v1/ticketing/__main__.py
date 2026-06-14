import uvicorn

from com.qode.qrew.v1.ticketing.settings import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.ticketing.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
