# entry point that starts the identity api server
import uvicorn

from com.qode.qrew.v1.identity.core.config import settings


# starts the identity api with uvicorn using the configured settings
def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.identity.app:app",
        reload=settings.debug,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
