from dataclasses import dataclass
from typing import Protocol

import jwt
import structlog

from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_GOOGLE_JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/play-integrity"


@dataclass(frozen=True)
class AttestationResult:
    platform: str


class AttestationVerifierError(Exception):
    """Raised when attestation cannot be verified."""


class AttestationVerifier(Protocol):
    async def verify_android(self, token: str, expected_nonce: str) -> AttestationResult: ...

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult: ...


class BypassVerifier:
    """Bypass attestation in development and staging."""

    async def verify_android(self, token: str, expected_nonce: str) -> AttestationResult:
        await logger.awarning("attestation_bypassed", platform="android")
        return AttestationResult(platform="bypass")

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        await logger.awarning("attestation_bypassed", platform="ios")
        return AttestationResult(platform="bypass")


class AndroidPlayIntegrityVerifier:
    """Validate a Google Play Integrity verdict."""

    async def verify_android(self, token: str, expected_nonce: str) -> AttestationResult:
        try:
            jwks_client = jwt.PyJWKClient(_GOOGLE_JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                options={"verify_aud": False},
            )
        except Exception as exc:
            raise AttestationVerifierError("App integrity rejected.") from exc

        request = payload.get("requestDetails", {})
        app_integrity = payload.get("appIntegrity", {})
        device_integrity = payload.get("deviceIntegrity", {})

        if request.get("nonce") != expected_nonce:
            raise AttestationVerifierError("Attestation rejected.")

        if request.get("requestPackageName") != settings.android_package_name:
            raise AttestationVerifierError("App integrity rejected.")

        if app_integrity.get("appRecognitionVerdict") != "PLAY_RECOGNIZED":
            raise AttestationVerifierError("App integrity rejected.")

        if app_integrity.get("packageName") != settings.android_package_name:
            raise AttestationVerifierError("App integrity rejected.")

        digests: list[str] = list(app_integrity.get("certificateSha256Digest") or [])
        if settings.android_app_cert_digest_sha256 not in digests:
            raise AttestationVerifierError("App integrity rejected.")

        verdicts = set(device_integrity.get("deviceRecognitionVerdict") or [])
        if "MEETS_DEVICE_INTEGRITY" not in verdicts:
            raise AttestationVerifierError("Device integrity rejected.")
        if "MEETS_BASIC_INTEGRITY" not in verdicts:
            raise AttestationVerifierError("Device integrity rejected.")
        if verdicts == {"MEETS_VIRTUAL_INTEGRITY"}:
            raise AttestationVerifierError("Device integrity rejected.")

        return AttestationResult(platform="android")

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        raise AttestationVerifierError("Token platform mismatched.")


class IosAppAttestVerifier:
    """Validate an Apple App Attest assertion."""

    async def verify_android(self, token: str, expected_nonce: str) -> AttestationResult:
        raise AttestationVerifierError("Token platform mismatched.")

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        """Validate an iOS App Attest assertion."""
        raise AttestationVerifierError(
            "iOS App Attest CA chain validation is not yet implemented — "
            "configure attestation_enabled=False or deploy after implementing full Apple attestation."
        )


def build_attestation_verifier() -> AttestationVerifier:
    """Build the attestation verifier configured by settings."""
    if not settings.attestation_enabled or settings.attestation_skip_verification:
        return BypassVerifier()
    return _CompositeVerifier()


class _CompositeVerifier:
    def __init__(self) -> None:
        self._android = AndroidPlayIntegrityVerifier()
        self._ios = IosAppAttestVerifier()

    async def verify_android(self, token: str, expected_nonce: str) -> AttestationResult:
        return await self._android.verify_android(token, expected_nonce)

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        return await self._ios.verify_ios(token, expected_nonce)
