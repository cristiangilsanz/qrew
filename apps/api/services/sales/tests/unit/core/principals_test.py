# covers the token signing and verification helpers of the sales service
import uuid

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from com.qode.qrew.v1.sales.core import principals
from com.qode.qrew.v1.sales.core.principals import Purpose


# builds a request stand in carrying the given headers
def _request(headers: dict[str, str]) -> object:
    class _Request:
        def __init__(self) -> None:
            self.headers = headers

    return _Request()


# builds bearer credentials around a raw token
def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestSignAndVerify:
    # verifies that a signed token verifies back to its payload
    def test_round_trip_returns_the_payload(self) -> None:
        token = principals.sign(Purpose.ACCESS, {"sub": "abc"})
        assert principals.verify(Purpose.ACCESS, token)["sub"] == "abc"

    # verifies that the key of a purpose is loaded once and cached
    def test_key_is_loaded_once_per_purpose(self) -> None:
        first = principals._get(Purpose.QUEUE)
        assert principals._get(Purpose.QUEUE) is first

    # verifies that each purpose gets its own key
    def test_each_purpose_has_its_own_key(self) -> None:
        assert principals._get(Purpose.ACCESS) != principals._get(Purpose.QUEUE)

    # verifies that a token signed for one purpose is refused by another
    def test_token_of_another_purpose_is_refused(self) -> None:
        token = principals.sign(Purpose.QUEUE, {"sub": "abc"})
        with pytest.raises(jwt.InvalidTokenError):
            principals.verify(Purpose.ACCESS, token)

    # verifies that verifying against several purposes reports the one that matched
    def test_verify_any_reports_the_purpose_that_matched(self) -> None:
        token = principals.sign(Purpose.QUEUE, {"sub": "abc"})
        purpose, payload = principals.verify_any((Purpose.ACCESS, Purpose.QUEUE), token)
        assert purpose is Purpose.QUEUE
        assert payload["sub"] == "abc"

    # verifies that a token matching no purpose is refused
    def test_verify_any_refuses_a_token_matching_no_purpose(self) -> None:
        stranger = principals._gen_ephemeral_pem()
        token = jwt.encode({"sub": "abc"}, stranger, algorithm="ES256")
        with pytest.raises(jwt.InvalidTokenError):
            principals.verify_any((Purpose.ACCESS, Purpose.QUEUE), token)


class TestGetCurrentUser:
    # verifies that the gateway header identifies the caller
    def test_header_identifies_the_caller(self) -> None:
        user_id = uuid.uuid4()
        user = principals.get_current_user(
            _request({"x-authenticated-user-id": str(user_id)}),  # type: ignore[arg-type]
            None,
        )
        assert user.id == user_id

    # verifies that a malformed header is rejected
    def test_malformed_header_is_rejected(self) -> None:
        with pytest.raises(HTTPException) as exc:
            principals.get_current_user(_request({"x-authenticated-user-id": "nope"}), None)  # type: ignore[arg-type]
        assert exc.value.status_code == 401

    # verifies that a request with neither header nor token is rejected
    def test_request_without_any_credential_is_rejected(self) -> None:
        with pytest.raises(HTTPException) as exc:
            principals.get_current_user(_request({}), None)  # type: ignore[arg-type]
        assert exc.value.status_code == 401

    # verifies that a bearer token identifies the caller
    def test_bearer_token_identifies_the_caller(self) -> None:
        user_id = uuid.uuid4()
        token = principals.sign(Purpose.ACCESS, {"sub": str(user_id)})
        user = principals.get_current_user(_request({}), _bearer(token))  # type: ignore[arg-type]
        assert user.id == user_id

    # verifies that a token without a subject is rejected
    def test_token_without_a_subject_is_rejected(self) -> None:
        token = principals.sign(Purpose.ACCESS, {"nothing": True})
        with pytest.raises(HTTPException) as exc:
            principals.get_current_user(_request({}), _bearer(token))  # type: ignore[arg-type]
        assert exc.value.status_code == 401
