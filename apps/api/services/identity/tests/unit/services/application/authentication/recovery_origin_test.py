# tests that recovery admits the same passkey origins the ordinary registration does
from unittest.mock import MagicMock, patch

import pytest
from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.services.application.authentication.account.recovery import (
    RecoveryError,
    RecoveryService,
)

_MODULE = "com.qode.qrew.v1.identity.services.application.authentication.account.recovery"


# builds a service whose collaborators are all stand ins, since only the verification matters
def _service() -> RecoveryService:
    return RecoveryService(*[MagicMock() for _ in range(8)])


# builds a registration response whose contents never reach the verifier
def _request() -> MagicMock:
    request = MagicMock()
    request.id = "credential-id"
    request.raw_id = "AAAA"
    request.response.client_data_json = "AAAA"
    request.response.attestation_object = "AAAA"
    return request


class TestTheOriginsRecoveryAccepts:
    # verifies that the native origin travels alongside the web one, since a handset
    # signs with its own and would otherwise never complete a recovery
    def test_it_admits_every_configured_origin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "rp_expected_origin", "https://qrew-dev.uk")
        monkeypatch.setattr(settings, "rp_expected_origins", ["android:apk-key-hash:abc"])
        with patch(f"{_MODULE}.webauthn.verify_registration_response") as verify:
            _service()._verify_attestation(b"challenge", _request())

        assert verify.call_args.kwargs["expected_origin"] == [
            "https://qrew-dev.uk",
            "android:apk-key-hash:abc",
        ]

    # verifies that a deployment declaring no extra origin still passes the single one
    def test_it_passes_the_lone_origin_when_no_other_is_declared(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "rp_expected_origin", "https://qrew-dev.uk")
        monkeypatch.setattr(settings, "rp_expected_origins", [])
        with patch(f"{_MODULE}.webauthn.verify_registration_response") as verify:
            _service()._verify_attestation(b"challenge", _request())

        assert verify.call_args.kwargs["expected_origin"] == "https://qrew-dev.uk"

    # verifies that a rejected ceremony still surfaces as a recovery error
    def test_it_reports_a_rejected_ceremony(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "rp_expected_origins", [])
        with patch(f"{_MODULE}.webauthn.verify_registration_response") as verify:
            verify.side_effect = ValueError("origin mismatch")
            with pytest.raises(RecoveryError, match="Passkey registration failed"):
                _service()._verify_attestation(b"challenge", _request())


class TestTheKeyRecoveryAsksFor:
    # verifies that the replacement is discoverable, since a platform stops offering a
    # credential it cannot enumerate and the holder is left without a way back in
    def test_it_demands_a_discoverable_credential(self) -> None:
        from webauthn.helpers.structs import ResidentKeyRequirement

        user = MagicMock()
        user.id = "9cfc6919-af7d-4e4d-9174-5b6f16fb1c05"
        user.email = "holder@qrew.dev"
        user.full_name = "Holder"
        options = _service()._generate_registration_options(user)

        assert options.authenticator_selection is not None
        assert options.authenticator_selection.resident_key is ResidentKeyRequirement.REQUIRED
