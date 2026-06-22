from com.qode.qrew.v1.identity.services.application.notification._masking import (
    mask_email,
    mask_phone_number,
)


class TestMaskEmail:
    def test_normal_email(self) -> None:
        assert mask_email("john.doe@example.com") == "j******e@example.com"

    def test_short_local_two_chars(self) -> None:
        assert mask_email("jo@example.com") == "j*@example.com"

    def test_single_char_local(self) -> None:
        assert mask_email("j@example.com") == "j*@example.com"

    def test_three_char_local(self) -> None:
        assert mask_email("joe@example.com") == "j*e@example.com"

    def test_no_at_sign_returns_placeholder(self) -> None:
        assert mask_email("notanemail") == "***@***"

    def test_preserves_domain(self) -> None:
        result = mask_email("alice@internal.company.org")
        assert result.endswith("@internal.company.org")


class TestMaskPhoneNumber:
    def test_standard_e164(self) -> None:
        result = mask_phone_number("+31612345678")
        assert result.endswith("5678")
        assert "*" in result

    def test_short_number_fewer_than_4_digits(self) -> None:
        assert mask_phone_number("123") == "****"

    def test_exactly_4_digits(self) -> None:
        assert mask_phone_number("1234") == "1234"

    def test_strips_non_digits(self) -> None:
        result = mask_phone_number("+1 (555) 123-4567")
        assert result.endswith("4567")

    def test_empty_string(self) -> None:
        assert mask_phone_number("") == "****"
