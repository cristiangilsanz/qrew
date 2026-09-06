# tests handlers
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
    # verifies that without field
    def test_without_field(self) -> None:
        body = _error_body("Something went wrong")
        assert body == {"detail": {"message": "Something went wrong", "field": None}}

    # verifies that with field
    def test_with_field(self) -> None:
        body = _error_body("Required", "email")
        assert body == {"detail": {"message": "Required", "field": "email"}}


class TestLocationToField:
    # verifies that single field
    def test_single_field(self) -> None:
        assert _location_to_field(("body", "email")) == "email"

    # verifies that nested field skips int index
    def test_nested_field_skips_int_index(self) -> None:
        assert _location_to_field(("body", "items", 0, "name")) == "items.name"

    # verifies that only root returns none
    def test_only_root_returns_none(self) -> None:
        assert _location_to_field(("body",)) is None


class TestCredentialsException:
    # verifies that returns 401
    def test_returns_401(self) -> None:
        exc = credentials_exception()
        assert exc.status_code == 401

    # verifies that has www authenticate header
    def test_has_www_authenticate_header(self) -> None:
        exc = credentials_exception()
        assert exc.headers is not None
        assert exc.headers.get("WWW-Authenticate") == "Bearer"


class TestHttpExceptionHandler:
    # verifies that plain string detail
    async def test_plain_string_detail(self) -> None:
        exc = HTTPException(status_code=404, detail="Not found")
        response = await _http_exception_handler(MagicMock(), exc)
        assert response.status_code == 404
        import json

        body = json.loads(response.body)
        assert body["detail"]["message"] == "Not found"

    # verifies that dict detail preserves message and field
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
    # verifies that picks first error and rewrites it in house style
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
        assert body["detail"]["message"] == "Email missing."
        assert body["detail"]["field"] == "email"

    # verifies that a value error keeps the wording the validator chose
    async def test_value_error_keeps_the_validator_wording(self) -> None:
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ("body", "phone_number"),
                    "msg": "Value error, Phone number is not valid.",
                    "type": "value_error",
                }
            ]
        )
        response = await _validation_exception_handler(MagicMock(), exc)
        import json

        body = json.loads(response.body)
        assert body["detail"]["message"] == "Phone number is not valid."
        assert body["detail"]["field"] == "phone_number"

    # verifies that empty errors returns generic message
    async def test_empty_errors_returns_generic_message(self) -> None:
        exc = RequestValidationError(errors=[])
        response = await _validation_exception_handler(MagicMock(), exc)
        import json

        body = json.loads(response.body)
        assert body["detail"]["message"] == "Validation error"


class TestRateLimitHandler:
    # verifies that returns 429 with detail
    async def test_returns_429_with_detail(self) -> None:
        exc = MagicMock()
        exc.detail = "5 per minute"
        response = await _rate_limit_handler(MagicMock(), exc)
        assert response.status_code == 429
        import json

        body = json.loads(response.body)
        assert "Rate limit exceeded" in body["detail"]["message"]
        assert "5 per minute" in body["detail"]["message"]
