# builds and verifies the webauthn assertions passkey flows exchange
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

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.passkey import PasskeyCredential
from com.qode.qrew.v1.identity.schemas.passkey import (
    PasskeyAuthenticationCompleteRequest,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

CHALLENGE_TTL_SECONDS = 300
ASSERT_CHALLENGE_TTL_SECONDS = 30
CHALLENGE_PREFIX = "webauthn:challenge:"
AUTH_CHALLENGE_PREFIX = "webauthn:auth:challenge:"
ASSERT_CHALLENGE_PREFIX = "webauthn:assert:challenge:"


class PasskeyError(DomainError):
    pass


# builds the redis key for a registration challenge
def challenge_key(user_id: uuid.UUID) -> str:
    return f"{CHALLENGE_PREFIX}{user_id}"


# builds the redis key for an authentication challenge
def auth_challenge_key(user_id: uuid.UUID) -> str:
    return f"{AUTH_CHALLENGE_PREFIX}{user_id}"


# builds the redis key for a reassertion challenge
def assert_challenge_key(session_jti: str) -> str:
    return f"{ASSERT_CHALLENGE_PREFIX}{session_jti}"


# builds the webauthn options offering an account's registered credentials
def build_authentication_options(
    credentials: list[PasskeyCredential],
) -> PublicKeyCredentialRequestOptions:
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


# converts a request payload into a webauthn assertion credential
def build_assertion_credential(
    request: PasskeyAuthenticationCompleteRequest,
) -> AuthenticationCredential:
    raw_id = base64url_to_bytes(request.raw_id)
    user_handle = (
        base64url_to_bytes(request.response.user_handle) if request.response.user_handle else None
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


# verifies a webauthn assertion against its stored credential
def verify_assertion_response(
    credential: AuthenticationCredential,
    expected_challenge: bytes,
    stored: PasskeyCredential,
) -> VerifiedAuthentication:
    expected_origins: str | list[str] = (
        [settings.rp_expected_origin] + settings.rp_expected_origins
        if settings.rp_expected_origins
        else settings.rp_expected_origin
    )
    return webauthn.verify_authentication_response(
        credential=credential,
        expected_challenge=expected_challenge,
        expected_rp_id=settings.rp_id,
        expected_origin=expected_origins,
        credential_current_sign_count=stored.sign_count,
        credential_public_key=stored.public_key,
        require_user_verification=True,
    )


# builds an error message that only reveals detail in debug mode
def assertion_error_message(exc: Exception, action_label: str) -> str:
    return (
        f"Passkey {action_label} failed: {exc}"
        if settings.debug
        else f"Passkey {action_label} failed. Please try again."
    )
