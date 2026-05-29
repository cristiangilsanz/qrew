from dataclasses import dataclass
from typing import Protocol

import jwt
import structlog

from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_GOOGLE_JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/play-integrity"


@dataclass(frozen=True)
class AttestationResult:
    platform: str


class AttestationVerifierError(Exception):
    """Raised when attestation cannot be verified."""


class AttestationVerifier(Protocol):
    async def verify_android(
        self, token: str, expected_nonce: str
    ) -> AttestationResult: ...

    async def verify_ios(
        self, token: str, expected_nonce: str
    ) -> AttestationResult: ...


class BypassVerifier:
    """Bypass attestation in development and staging."""

    async def verify_android(
        self, token: str, expected_nonce: str
    ) -> AttestationResult:
        await logger.awarning("attestation_bypassed", platform="android")
        return AttestationResult(platform="bypass")

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        await logger.awarning("attestation_bypassed", platform="ios")
        return AttestationResult(platform="bypass")


class AndroidPlayIntegrityVerifier:
    """Validate a Google Play Integrity verdict."""

    async def verify_android(
        self, token: str, expected_nonce: str
    ) -> AttestationResult:
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
            raise AttestationVerifierError(
                "Play Integrity token signature invalid"
            ) from exc

        request = payload.get("requestDetails", {})
        app_integrity = payload.get("appIntegrity", {})
        device_integrity = payload.get("deviceIntegrity", {})

        if request.get("nonce") != expected_nonce:
            raise AttestationVerifierError("Attestation nonce mismatch")

        if request.get("requestPackageName") != settings.android_package_name:
            raise AttestationVerifierError("Unexpected package name")

        if app_integrity.get("appRecognitionVerdict") != "PLAY_RECOGNIZED":
            raise AttestationVerifierError("App not recognised by Play")

        if app_integrity.get("packageName") != settings.android_package_name:
            raise AttestationVerifierError("App integrity package name mismatch")

        digests: list[str] = list(app_integrity.get("certificateSha256Digest") or [])
        if settings.android_app_cert_digest_sha256 not in digests:
            raise AttestationVerifierError("App signing cert digest mismatch")

        verdicts = set(device_integrity.get("deviceRecognitionVerdict") or [])
        if "MEETS_DEVICE_INTEGRITY" not in verdicts:
            raise AttestationVerifierError("Device fails MEETS_DEVICE_INTEGRITY")
        if "MEETS_BASIC_INTEGRITY" not in verdicts:
            raise AttestationVerifierError("Device fails MEETS_BASIC_INTEGRITY")
        if verdicts == {"MEETS_VIRTUAL_INTEGRITY"}:
            raise AttestationVerifierError("Virtual/emulator-only verdict not accepted")

        return AttestationResult(platform="android")

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        raise AttestationVerifierError("Android verifier cannot verify iOS tokens")


class IosAppAttestVerifier:
    """Validate an Apple App Attest assertion."""

    async def verify_android(
        self, token: str, expected_nonce: str
    ) -> AttestationResult:
        raise AttestationVerifierError("iOS verifier cannot verify Android tokens")

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        """Validate an iOS App Attest assertion."""
        # TODO: implement full Apple App Attest CA chain validation
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_aud": False},
            )
        except Exception as exc:
            raise AttestationVerifierError("Invalid App Attest token") from exc

        if payload.get("nonce") != expected_nonce:
            raise AttestationVerifierError("Attestation nonce mismatch")
        if payload.get("teamId") != settings.ios_team_id:
            raise AttestationVerifierError("Unexpected team id")
        if payload.get("bundleId") != settings.ios_bundle_id:
            raise AttestationVerifierError("Unexpected bundle id")

        return AttestationResult(platform="ios")


def build_attestation_verifier() -> AttestationVerifier:
    """Build the attestation verifier configured by settings."""
    if not settings.attestation_enabled or settings.attestation_dev_bypass:
        return BypassVerifier()
    return _CompositeVerifier()


class _CompositeVerifier:
    def __init__(self) -> None:
        self._android = AndroidPlayIntegrityVerifier()
        self._ios = IosAppAttestVerifier()

    async def verify_android(
        self, token: str, expected_nonce: str
    ) -> AttestationResult:
        return await self._android.verify_android(token, expected_nonce)

    async def verify_ios(self, token: str, expected_nonce: str) -> AttestationResult:
        return await self._ios.verify_ios(token, expected_nonce)
