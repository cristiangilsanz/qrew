import uvicorn

from com.qode.qrew.v1.gateway.settings import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.gateway.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
