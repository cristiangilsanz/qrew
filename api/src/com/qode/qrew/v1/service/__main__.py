import uvicorn


def main() -> None:
    uvicorn.run(
        "com.qode.qrew.v1.service.main:app",
        reload=True,
        host="0.0.0.0",
        port=8000,
    )
