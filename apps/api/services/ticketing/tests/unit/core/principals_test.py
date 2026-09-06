# covers the token signing and verification helpers of the ticketing service
import uuid

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from com.qode.qrew.v1.ticketing.core import principals


# builds a request stand in carrying the given headers
def _request(headers: dict[str, str]) -> object:
    class _Request:
        def __init__(self) -> None:
            self.headers = headers

    return _Request()


# builds bearer credentials around a raw token
def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestKeyHelpers:
    # verifies that a key identifier is stable and short
    def test_kid_is_stable_and_short(self) -> None:
        kid = principals.kid_for(principals.ACCESS)
        assert len(kid) == 16
        assert principals.kid_for(principals.ACCESS) == kid

    # verifies that each purpose gets its own key
    def test_each_purpose_has_its_own_key(self) -> None:
        assert principals.kid_for(principals.ACCESS) != principals.kid_for(principals.TICKET_QR)

    # verifies that a concatenated block splits into one entry per key
    def test_split_pems_splits_a_concatenated_block(self) -> None:
        block = (
            "-----BEGIN PUBLIC KEY-----\naaa\n-----END PUBLIC KEY-----\n"
            "-----BEGIN PUBLIC KEY-----\nbbb\n-----END PUBLIC KEY-----\n"
        )
        assert len(principals._split_pems(block)) == 2

    # verifies that an empty block yields no keys
    def test_split_pems_of_an_empty_block_is_empty(self) -> None:
        assert principals._split_pems("") == []

    # verifies that a derived public key matches the one generated beside it
    def test_derived_public_key_matches_the_generated_one(self) -> None:
        private_pem, public_pem = principals._generate_ephemeral_keypair()
        assert principals._derive_public_pem(private_pem) == public_pem


class TestSignAndVerify:
    # verifies that a signed token verifies back to its claims
    def test_round_trip_returns_the_claims(self) -> None:
        token = principals.sign(principals.ACCESS, {"sub": "abc"})
        assert principals.verify(principals.ACCESS, token)["sub"] == "abc"

    # verifies that a token carries the key identifier in its header
    def test_signed_token_names_its_key(self) -> None:
        token = principals.sign(principals.TICKET_QR, {"sub": "abc"})
        header = jwt.get_unverified_header(token)
        assert header["kid"] == principals.kid_for(principals.TICKET_QR)

    # verifies that a token signed for one purpose is refused by another
    def test_token_of_another_purpose_is_refused(self) -> None:
        token = principals.sign(principals.TICKET_QR, {"sub": "abc"})
        with pytest.raises(jwt.InvalidTokenError):
            principals.verify(principals.ACCESS, token)


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

    # verifies that a bearer token identifies the caller and its device
    def test_bearer_token_identifies_the_caller_and_device(self) -> None:
        user_id, device_id = uuid.uuid4(), uuid.uuid4()
        token = principals.sign(
            principals.ACCESS,
            {"sub": str(user_id), "device_id": str(device_id), "last_asserted_at": 1_700_000_000},
        )
        user = principals.get_current_user(_request({}), _bearer(token))  # type: ignore[arg-type]
        assert user.id == user_id
        assert user.device_id == device_id
        assert user.last_asserted_at is not None

    # verifies that a token without a subject is rejected
    def test_token_without_a_subject_is_rejected(self) -> None:
        token = principals.sign(principals.ACCESS, {"device_id": str(uuid.uuid4())})
        with pytest.raises(HTTPException) as exc:
            principals.get_current_user(_request({}), _bearer(token))  # type: ignore[arg-type]
        assert exc.value.status_code == 401

    # verifies that a token signed by an unknown key is rejected
    def test_token_signed_by_an_unknown_key_is_rejected(self) -> None:
        private_pem, _ = principals._generate_ephemeral_keypair()
        token = jwt.encode(
            {"sub": str(uuid.uuid4())}, private_pem, algorithm="ES256", headers={"kid": "nope"}
        )
        with pytest.raises(HTTPException) as exc:
            principals.get_current_user(_request({}), _bearer(token))  # type: ignore[arg-type]
        assert exc.value.status_code == 401
