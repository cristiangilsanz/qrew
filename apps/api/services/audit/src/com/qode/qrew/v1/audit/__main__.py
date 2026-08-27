# entry point that starts the audit api server
import uvicorn

from com.qode.qrew.v1.audit.core.config import settings


# starts the audit api with uvicorn using the configured settings
def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.audit.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
