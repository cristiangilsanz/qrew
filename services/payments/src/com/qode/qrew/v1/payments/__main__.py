import uvicorn

from com.qode.qrew.v1.payments.settings import settings


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.payments.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
