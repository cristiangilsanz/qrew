"""Ensure every error response in the public OpenAPI schema uses ErrorResponse."""

from typing import Any

from com.qode.qrew.v1.service.main import app

_ERROR_REF = "#/components/schemas/ErrorResponse"


def _all_responses(
    schema: dict[str, Any],
) -> list[tuple[str, str, str, dict[str, Any]]]:
    out: list[tuple[str, str, str, dict[str, Any]]] = []
    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            for status_code, body in operation.get("responses", {}).items():
                out.append((path, method, status_code, body))
    return out


def test_openapi_advertises_error_response_on_every_4xx_and_5xx() -> None:
    schema = app.openapi()

    offenders: list[str] = []
    for path, method, status_code, body in _all_responses(schema):
        try:
            code = int(status_code)
        except ValueError:
            continue
        if code < 400:
            continue
        content = body.get("content", {}).get("application/json", {})
        schema_ref = content.get("schema", {}).get("$ref")
        if schema_ref != _ERROR_REF:
            offenders.append(f"{method.upper()} {path} {status_code}")

    assert not offenders, f"Error responses missing ErrorResponse model: {offenders}"


def test_openapi_includes_error_response_schema() -> None:
    schema = app.openapi()
    components = schema.get("components", {}).get("schemas", {})
    assert "ErrorResponse" in components
    assert "ErrorDetail" in components
