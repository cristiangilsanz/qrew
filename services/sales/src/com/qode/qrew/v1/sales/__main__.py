import uvicorn

from com.qode.qrew.v1.sales.settings import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.sales.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
