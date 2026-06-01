from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from com.qode.qrew.v1.service.core.api import (
    default_responses,
    register_exception_handlers,
)


def _build_app() -> FastAPI:
    app = FastAPI(responses=default_responses)
    register_exception_handlers(app)

    class Body(BaseModel):
        name: str

    async def raises_string() -> None:
        raise HTTPException(status_code=404, detail="Not found")

    async def raises_dict() -> None:
        raise HTTPException(
            status_code=409, detail={"message": "Conflict here", "field": "name"}
        )

    async def validated(body: Body) -> dict[str, str]:
        return {"name": body.name}

    async def with_header() -> None:
        raise HTTPException(
            status_code=429,
            detail={"message": "Slow down", "field": None},
            headers={"Retry-After": "10"},
        )

    async def boom() -> None:
        raise RuntimeError("kaboom")

    app.add_api_route("/raises-string", raises_string, methods=["GET"])
    app.add_api_route("/raises-dict", raises_dict, methods=["GET"])
    app.add_api_route("/validated", validated, methods=["POST"])
    app.add_api_route("/with-header", with_header, methods=["GET"])
    app.add_api_route("/boom", boom, methods=["GET"])

    return app


def test_string_detail_is_wrapped() -> None:
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        r = client.get("/raises-string")
    assert r.status_code == 404
    assert r.json() == {"detail": {"message": "Not found", "field": None}}


def test_dict_detail_is_passed_through() -> None:
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        r = client.get("/raises-dict")
    assert r.status_code == 409
    assert r.json() == {"detail": {"message": "Conflict here", "field": "name"}}


def test_validation_error_maps_first_field() -> None:
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        r = client.post("/validated", json={})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body
    assert body["detail"]["field"] == "name"
    assert isinstance(body["detail"]["message"], str)


def test_headers_propagated_from_http_exception() -> None:
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        r = client.get("/with-header")
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "10"


def test_unhandled_exception_returns_500_with_canonical_body() -> None:
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        r = client.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"detail": {"message": "Internal server error", "field": None}}
