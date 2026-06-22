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
    def test_returns_multifernet(self) -> None:
        f = make_fernet(KEY)
        assert isinstance(f, MultiFernet)

    def test_with_previous_key(self) -> None:
        prev = Fernet.generate_key().decode()
        f = make_fernet(KEY, prev)
        assert isinstance(f, MultiFernet)

    def test_ignores_blank_previous_key_lines(self) -> None:
        f = make_fernet(KEY, "\n  \n")
        assert isinstance(f, MultiFernet)


class TestEncryptDecrypt:
    def test_round_trip(self) -> None:
        f = make_fernet(KEY)
        assert decrypt(f, encrypt(f, "hello")) == "hello"

    def test_empty_string(self) -> None:
        f = make_fernet(KEY)
        assert decrypt(f, encrypt(f, "")) == ""

    def test_ciphertexts_are_unique(self) -> None:
        f = make_fernet(KEY)
        assert encrypt(f, "same") != encrypt(f, "same")


class TestEncryptDecryptBytes:
    def test_round_trip(self) -> None:
        f = make_fernet(KEY)
        assert decrypt_bytes(f, encrypt_bytes(f, b"hello")) == b"hello"

    def test_binary_data(self) -> None:
        f = make_fernet(KEY)
        data = bytes(range(256))
        assert decrypt_bytes(f, encrypt_bytes(f, data)) == data


class TestKeyRotation:
    def test_rotated_fernet_decrypts_old_ciphertext(self) -> None:
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()
        old_fernet = make_fernet(old_key)
        ciphertext = encrypt(old_fernet, "secret")
        rotated = make_fernet(new_key, old_key)
        assert decrypt(rotated, ciphertext) == "secret"


class TestHashLookup:
    def test_case_insensitive(self) -> None:
        assert hash_lookup("Email@Example.COM") == hash_lookup("email@example.com")

    def test_strips_whitespace(self) -> None:
        assert hash_lookup("  test  ") == hash_lookup("test")

    def test_different_values_differ(self) -> None:
        assert hash_lookup("a") != hash_lookup("b")

    def test_returns_hex_string(self) -> None:
        result = hash_lookup("test")
        assert isinstance(result, str)
        int(result, 16)
