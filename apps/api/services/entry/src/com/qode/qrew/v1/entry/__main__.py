# entry point that starts the entry api server
import uvicorn

from com.qode.qrew.v1.entry.core.config import settings


# starts the entry api with uvicorn using the configured settings
def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.entry.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
