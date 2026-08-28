# entry point that starts the ticketing api server
import uvicorn

from com.qode.qrew.v1.ticketing.core.config import settings


# starts the ticketing api with uvicorn using the configured settings
def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.ticketing.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
