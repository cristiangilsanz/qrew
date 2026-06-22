from unittest.mock import MagicMock

from exceptions.handlers import (
    _error_body,
    _http_exception_handler,
    _location_to_field,
    _rate_limit_handler,
    _validation_exception_handler,
    credentials_exception,
)
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError


class TestErrorBody:
    def test_without_field(self) -> None:
        body = _error_body("Something went wrong")
        assert body == {"detail": {"message": "Something went wrong", "field": None}}

    def test_with_field(self) -> None:
        body = _error_body("Required", "email")
        assert body == {"detail": {"message": "Required", "field": "email"}}


class TestLocationToField:
    def test_single_field(self) -> None:
        assert _location_to_field(("body", "email")) == "email"

    def test_nested_field_skips_int_index(self) -> None:
        assert _location_to_field(("body", "items", 0, "name")) == "items.name"

    def test_only_root_returns_none(self) -> None:
        assert _location_to_field(("body",)) is None


class TestCredentialsException:
    def test_returns_401(self) -> None:
        exc = credentials_exception()
        assert exc.status_code == 401

    def test_has_www_authenticate_header(self) -> None:
        exc = credentials_exception()
        assert exc.headers is not None
        assert exc.headers.get("WWW-Authenticate") == "Bearer"


class TestHttpExceptionHandler:
    async def test_plain_string_detail(self) -> None:
        exc = HTTPException(status_code=404, detail="Not found")
        response = await _http_exception_handler(MagicMock(), exc)
        assert response.status_code == 404
        import json

        body = json.loads(response.body)
        assert body["detail"]["message"] == "Not found"

    async def test_dict_detail_preserves_message_and_field(self) -> None:
        exc = HTTPException(
            status_code=422, detail={"message": "Bad input", "field": "email"}
        )
        response = await _http_exception_handler(MagicMock(), exc)
        import json

        body = json.loads(response.body)
        assert body["detail"]["message"] == "Bad input"
        assert body["detail"]["field"] == "email"


class TestValidationExceptionHandler:
    async def test_picks_first_error_and_extracts_field(self) -> None:
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ("body", "email"),
                    "msg": "field required",
                    "type": "missing",
                }
            ]
        )
        response = await _validation_exception_handler(MagicMock(), exc)
        assert response.status_code == 422
        import json

        body = json.loads(response.body)
        assert body["detail"]["message"] == "field required"
        assert body["detail"]["field"] == "email"

    async def test_empty_errors_returns_generic_message(self) -> None:
        exc = RequestValidationError(errors=[])
        response = await _validation_exception_handler(MagicMock(), exc)
        import json

        body = json.loads(response.body)
        assert body["detail"]["message"] == "Validation error"


class TestRateLimitHandler:
    async def test_returns_429_with_detail(self) -> None:
        exc = MagicMock()
        exc.detail = "5 per minute"
        response = await _rate_limit_handler(MagicMock(), exc)
        assert response.status_code == 429
        import json

        body = json.loads(response.body)
        assert "Rate limit exceeded" in body["detail"]["message"]
        assert "5 per minute" in body["detail"]["message"]
