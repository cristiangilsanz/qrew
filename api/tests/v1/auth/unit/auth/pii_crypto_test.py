"""Tests for the PII encrypt/decrypt/hash helpers."""

import pytest
from cryptography.fernet import InvalidToken

from com.qode.qrew.v1.service.core.auth import pii_crypto


def test_encrypt_then_decrypt_roundtrip() -> None:
    plaintext = "alice@example.com"
    cipher = pii_crypto.encrypt(plaintext)
    assert cipher != plaintext.encode()
    assert pii_crypto.decrypt(cipher) == plaintext


def test_encrypt_produces_distinct_ciphertexts_for_same_input() -> None:
    one = pii_crypto.encrypt("alice@example.com")
    two = pii_crypto.encrypt("alice@example.com")
    assert one != two
    assert pii_crypto.decrypt(one) == pii_crypto.decrypt(two)


def test_hash_lookup_is_deterministic() -> None:
    assert pii_crypto.hash_lookup("alice@example.com") == pii_crypto.hash_lookup(
        "alice@example.com"
    )


def test_hash_lookup_normalises_case_and_whitespace() -> None:
    assert pii_crypto.hash_lookup("Alice@Example.com") == pii_crypto.hash_lookup(
        "  alice@example.com  "
    )


def test_hash_lookup_differs_per_input() -> None:
    assert pii_crypto.hash_lookup("a@b.com") != pii_crypto.hash_lookup("c@d.com")


def test_decrypt_rejects_tampered_ciphertext() -> None:
    cipher = pii_crypto.encrypt("alice@example.com")
    tampered = bytearray(cipher)
    tampered[-5] ^= 0x01
    with pytest.raises(InvalidToken):
        pii_crypto.decrypt(bytes(tampered))
