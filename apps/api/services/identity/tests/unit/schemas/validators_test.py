# covers the phone password and email validators shared across the identity schemas
import pytest

from com.qode.qrew.v1.identity.schemas._validators import (
    validate_non_disposable_email,
    validate_phone_number,
    validate_strong_password,
)


class TestValidatePhoneNumber:
    # verifies that a valid international number is accepted unchanged
    @pytest.mark.parametrize("number", ["+34612345678", "+447911123456", "+33612345678"])
    def test_accepts_a_valid_international_number(self, number: str) -> None:
        assert validate_phone_number(number) == number

    # verifies that a number without a country prefix is rejected
    def test_rejects_a_number_without_a_country_prefix(self) -> None:
        with pytest.raises(ValueError, match="Phone number rejected."):
            validate_phone_number("612345678")

    # verifies that a number that parses but is not assignable is rejected
    def test_rejects_an_unassignable_number(self) -> None:
        with pytest.raises(ValueError, match="Phone number rejected."):
            validate_phone_number("+34000000000")

    # verifies that text that is not a number at all is rejected
    def test_rejects_text_that_is_not_a_number(self) -> None:
        with pytest.raises(ValueError, match="Phone number rejected."):
            validate_phone_number("not a phone")


class TestValidateStrongPassword:
    # verifies that a strong password is accepted unchanged
    def test_accepts_a_strong_password(self) -> None:
        assert validate_strong_password("correct horse battery staple") is not None

    # verifies that a common password is rejected
    @pytest.mark.parametrize("password", ["password", "123456", "qwerty"])
    def test_rejects_a_common_password(self, password: str) -> None:
        with pytest.raises(ValueError):
            validate_strong_password(password)


class TestValidateNonDisposableEmail:
    # verifies that an ordinary address is accepted and lowercased
    def test_accepts_and_lowercases_an_ordinary_address(self) -> None:
        assert validate_non_disposable_email("Jane.Doe@Example.com") == "jane.doe@example.com"

    # verifies that a disposable address is rejected
    def test_rejects_a_disposable_address(self) -> None:
        with pytest.raises(ValueError, match="Disposable email rejected."):
            validate_non_disposable_email("someone@mailinator.com")
