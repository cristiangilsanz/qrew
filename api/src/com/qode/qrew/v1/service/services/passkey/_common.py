import uuid

import structlog
import webauthn
from webauthn.authentication.verify_authentication_response import (
    VerifiedAuthentication,
)
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticationCredential,
    AuthenticatorAssertionResponse,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    PublicKeyCredentialType,
    UserVerificationRequirement,
)

from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.models.passkey.passkey import PasskeyCredential
from com.qode.qrew.v1.service.schemas.passkey.passkey import (
    PasskeyAuthenticationCompleteRequest,
)
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

CHALLENGE_TTL_SECONDS = 300
ASSERT_CHALLENGE_TTL_SECONDS = 30
CHALLENGE_PREFIX = "webauthn:challenge:"
AUTH_CHALLENGE_PREFIX = "webauthn:auth:challenge:"
ASSERT_CHALLENGE_PREFIX = "webauthn:assert:challenge:"


class PasskeyError(DomainError):
    """Raised when a passkey operation cannot be completed."""


def challenge_key(user_id: uuid.UUID) -> str:
    """Return the Redis key for a pending registration challenge."""
    return f"{CHALLENGE_PREFIX}{user_id}"


def auth_challenge_key(user_id: uuid.UUID) -> str:
    """Return the Redis key for a pending authentication challenge."""
    return f"{AUTH_CHALLENGE_PREFIX}{user_id}"


def assert_challenge_key(session_jti: str) -> str:
    """Return the Redis key for a pending re-assertion challenge."""
    return f"{ASSERT_CHALLENGE_PREFIX}{session_jti}"


def build_authentication_options(
    credentials: list[PasskeyCredential],
) -> PublicKeyCredentialRequestOptions:
    """Generate WebAuthn assertion options for a user's credentials."""
    allowed = [
        PublicKeyCredentialDescriptor(
            id=c.credential_id,
            type=PublicKeyCredentialType.PUBLIC_KEY,
        )
        for c in credentials
    ]
    return webauthn.generate_authentication_options(
        rp_id=settings.rp_id,
        allow_credentials=allowed,
        user_verification=UserVerificationRequirement.REQUIRED,
    )


def build_assertion_credential(
    request: PasskeyAuthenticationCompleteRequest,
) -> AuthenticationCredential:
    """Build a WebAuthn assertion credential from a request body."""
    raw_id = base64url_to_bytes(request.raw_id)
    user_handle = (
        base64url_to_bytes(request.response.user_handle)
        if request.response.user_handle
        else None
    )
    return AuthenticationCredential(
        id=request.id,
        raw_id=raw_id,
        response=AuthenticatorAssertionResponse(
            client_data_json=base64url_to_bytes(request.response.client_data_json),
            authenticator_data=base64url_to_bytes(request.response.authenticator_data),
            signature=base64url_to_bytes(request.response.signature),
            user_handle=user_handle,
        ),
        type=PublicKeyCredentialType.PUBLIC_KEY,
    )


def verify_assertion_response(
    credential: AuthenticationCredential,
    expected_challenge: bytes,
    stored: PasskeyCredential,
) -> VerifiedAuthentication:
    """Verify a passkey assertion against the stored public key."""
    return webauthn.verify_authentication_response(
        credential=credential,
        expected_challenge=expected_challenge,
        expected_rp_id=settings.rp_id,
        expected_origin=settings.rp_expected_origin,
        credential_current_sign_count=stored.sign_count,
        credential_public_key=stored.public_key,
        require_user_verification=True,
    )


def assertion_error_message(exc: Exception, action_label: str) -> str:
    """Build a passkey assertion error message tuned to the debug flag."""
    return (
        f"Passkey {action_label} failed: {exc}"
        if settings.debug
        else f"Passkey {action_label} failed. Please try again."
    )
