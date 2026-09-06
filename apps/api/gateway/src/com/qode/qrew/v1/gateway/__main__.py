# entry point that starts the gateway api server
import uvicorn

from com.qode.qrew.v1.gateway.core.config import settings


# starts the gateway api with uvicorn using the configured settings
def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.gateway.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
