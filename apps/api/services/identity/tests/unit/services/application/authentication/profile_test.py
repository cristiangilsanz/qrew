# tests which onboarding step an account is sent to for each state it can be in
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.identity.models.user import KycStatus
from com.qode.qrew.v1.identity.services.application.authentication.profile import ProfileService


# builds a user that has cleared every step before the one under test
def _user(
    *,
    kyc_status: KycStatus = KycStatus.approved,
    email_verified: bool = True,
    phone_verified: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        phone_number="+34612345678",
        email_verified=email_verified,
        phone_number_verified=phone_verified,
        kyc_status=kyc_status,
    )


# builds a profile service whose passkey lookup answers as told
def _service(*, has_passkey: bool) -> ProfileService:
    repo = MagicMock()
    repo.has_passkey = AsyncMock(return_value=has_passkey)
    return ProfileService(repo)


class TestOnboardingStatus:
    # verifies that an unverified address stops the wizard at the first step
    async def test_an_unverified_address_stops_at_the_email_step(self) -> None:
        status = await _service(has_passkey=True).get_onboarding_status(
            _user(email_verified=False)  # type: ignore[arg-type]
        )
        assert status.current_step == "email"
        assert status.is_complete is False

    # verifies that an unverified phone stops the wizard at the second step
    async def test_an_unverified_phone_stops_at_the_phone_step(self) -> None:
        status = await _service(has_passkey=True).get_onboarding_status(
            _user(phone_verified=False)  # type: ignore[arg-type]
        )
        assert status.current_step == "phone"

    # verifies that an account that never submitted is asked for its document
    async def test_an_account_without_a_document_is_asked_for_one(self) -> None:
        status = await _service(has_passkey=True).get_onboarding_status(
            _user(kyc_status=KycStatus.not_submitted)  # type: ignore[arg-type]
        )
        assert status.current_step == "kyc"
        assert status.kyc_submitted is False

    # verifies that an account still missing a passkey is asked for one
    async def test_an_account_without_a_passkey_is_asked_for_one(self) -> None:
        status = await _service(has_passkey=False).get_onboarding_status(_user())  # type: ignore[arg-type]
        assert status.current_step == "passkey"

    # verifies that a submission awaiting review parks the account on the waiting screen
    async def test_a_submission_under_review_waits(self) -> None:
        status = await _service(has_passkey=True).get_onboarding_status(
            _user(kyc_status=KycStatus.pending)  # type: ignore[arg-type]
        )
        assert status.current_step == "pending"
        assert status.kyc_status == "pending"
        assert status.is_complete is False

    # verifies that an approved account has finished
    async def test_an_approved_account_is_complete(self) -> None:
        status = await _service(has_passkey=True).get_onboarding_status(_user())  # type: ignore[arg-type]
        assert status.is_complete is True

    # verifies that a rejected document is reported so the screen can say so
    async def test_a_rejected_document_is_reported_as_rejected(self) -> None:
        status = await _service(has_passkey=True).get_onboarding_status(
            _user(kyc_status=KycStatus.rejected)  # type: ignore[arg-type]
        )
        assert status.kyc_status == "rejected"
        assert status.current_step == "pending"

    # verifies that a rejected document never counts as a finished setup
    async def test_a_rejected_document_never_completes_setup(self) -> None:
        status = await _service(has_passkey=True).get_onboarding_status(
            _user(kyc_status=KycStatus.rejected)  # type: ignore[arg-type]
        )
        assert status.is_complete is False

    # verifies that a rejected account is not sent back to the passkey step it already cleared
    @pytest.mark.parametrize("has_passkey", [True, False])
    async def test_a_rejected_account_lands_on_the_same_screen_either_way(
        self, has_passkey: bool
    ) -> None:
        status = await _service(has_passkey=has_passkey).get_onboarding_status(
            _user(kyc_status=KycStatus.rejected)  # type: ignore[arg-type]
        )
        assert status.current_step == "pending"
