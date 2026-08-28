# tests pii
from cryptography.fernet import Fernet, MultiFernet
from security.pii import (
    decrypt,
    decrypt_bytes,
    encrypt,
    encrypt_bytes,
    hash_lookup,
    make_fernet,
)

KEY = Fernet.generate_key().decode()


class TestMakeFernet:
    # verifies that returns multifernet
    def test_returns_multifernet(self) -> None:
        f = make_fernet(KEY)
        assert isinstance(f, MultiFernet)

    # verifies that with previous key
    def test_with_previous_key(self) -> None:
        prev = Fernet.generate_key().decode()
        f = make_fernet(KEY, prev)
        assert isinstance(f, MultiFernet)

    # verifies that ignores blank previous key lines
    def test_ignores_blank_previous_key_lines(self) -> None:
        f = make_fernet(KEY, "\n  \n")
        assert isinstance(f, MultiFernet)


class TestEncryptDecrypt:
    # verifies that round trip
    def test_round_trip(self) -> None:
        f = make_fernet(KEY)
        assert decrypt(f, encrypt(f, "hello")) == "hello"

    # verifies that empty string
    def test_empty_string(self) -> None:
        f = make_fernet(KEY)
        assert decrypt(f, encrypt(f, "")) == ""

    # verifies that ciphertexts are unique
    def test_ciphertexts_are_unique(self) -> None:
        f = make_fernet(KEY)
        assert encrypt(f, "same") != encrypt(f, "same")


class TestEncryptDecryptBytes:
    # verifies that round trip
    def test_round_trip(self) -> None:
        f = make_fernet(KEY)
        assert decrypt_bytes(f, encrypt_bytes(f, b"hello")) == b"hello"

    # verifies that binary data
    def test_binary_data(self) -> None:
        f = make_fernet(KEY)
        data = bytes(range(256))
        assert decrypt_bytes(f, encrypt_bytes(f, data)) == data


class TestKeyRotation:
    # verifies that rotated fernet decrypts old ciphertext
    def test_rotated_fernet_decrypts_old_ciphertext(self) -> None:
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()
        old_fernet = make_fernet(old_key)
        ciphertext = encrypt(old_fernet, "secret")
        rotated = make_fernet(new_key, old_key)
        assert decrypt(rotated, ciphertext) == "secret"


class TestHashLookup:
    # verifies that case insensitive
    def test_case_insensitive(self) -> None:
        assert hash_lookup("Email@Example.COM") == hash_lookup("email@example.com")

    # verifies that strips whitespace
    def test_strips_whitespace(self) -> None:
        assert hash_lookup("  test  ") == hash_lookup("test")

    # verifies that different values differ
    def test_different_values_differ(self) -> None:
        assert hash_lookup("a") != hash_lookup("b")

    # verifies that returns hex string
    def test_returns_hex_string(self) -> None:
        result = hash_lookup("test")
        assert isinstance(result, str)
        int(result, 16)
