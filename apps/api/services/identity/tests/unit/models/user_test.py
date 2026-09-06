# covers the encrypted properties the user model exposes over its ciphertext columns
from com.qode.qrew.v1.identity.models.user import User


class TestEncryptedProperties:
    # verifies that an email is stored encrypted and read back in the clear
    def test_email_round_trips_through_the_ciphertext(self) -> None:
        user = User()
        user.email = "jane@example.com"
        assert user.email_ciphertext is not None
        assert user.email_ciphertext != b"jane@example.com"
        assert user.email == "jane@example.com"

    # verifies that an email is hashed so it can be looked up without decrypting
    def test_email_is_hashed_for_lookup(self) -> None:
        first, second = User(), User()
        first.email = "jane@example.com"
        second.email = "jane@example.com"
        assert first.email_hash == second.email_hash
        assert first.email_ciphertext != second.email_ciphertext

    # verifies that a phone number round trips and is hashed for lookup
    def test_phone_number_round_trips_and_is_hashed(self) -> None:
        user = User()
        user.phone_number = "+34612345678"
        assert user.phone_number == "+34612345678"
        assert user.phone_number_hash is not None

    # verifies that a full name round trips
    def test_full_name_round_trips(self) -> None:
        user = User()
        user.full_name = "Jane Doe"
        assert user.full_name == "Jane Doe"

    # verifies that a totp secret round trips
    def test_totp_secret_round_trips(self) -> None:
        user = User()
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        assert user.totp_secret == "JBSWY3DPEHPK3PXP"

    # verifies that clearing the totp secret leaves nothing stored
    def test_clearing_the_totp_secret_leaves_nothing(self) -> None:
        user = User()
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.totp_secret = None
        assert user.totp_secret is None
        assert user.totp_secret_ciphertext is None

    # verifies that a pending email round trips and is hashed for lookup
    def test_pending_email_round_trips_and_is_hashed(self) -> None:
        user = User()
        user.pending_email = "new@example.com"
        assert user.pending_email == "new@example.com"
        assert user.pending_email_hash is not None

    # verifies that clearing a pending email clears its lookup hash too
    def test_clearing_the_pending_email_clears_its_hash(self) -> None:
        user = User()
        user.pending_email = "new@example.com"
        user.pending_email = None
        assert user.pending_email is None
        assert user.pending_email_hash is None

    # verifies that a pending phone number round trips and is hashed for lookup
    def test_pending_phone_number_round_trips_and_is_hashed(self) -> None:
        user = User()
        user.pending_phone_number = "+34612345678"
        assert user.pending_phone_number == "+34612345678"
        assert user.pending_phone_number_hash is not None

    # verifies that clearing a pending phone number clears its lookup hash too
    def test_clearing_the_pending_phone_number_clears_its_hash(self) -> None:
        user = User()
        user.pending_phone_number = "+34612345678"
        user.pending_phone_number = None
        assert user.pending_phone_number is None
        assert user.pending_phone_number_hash is None
