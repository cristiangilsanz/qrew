from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto

ENCRYPTED_KINDS = frozenset({"kyc"})


def should_encrypt(kind: str) -> bool:
    """Return whether a kind must be encrypted at rest."""
    return kind in ENCRYPTED_KINDS


def encrypt(content: bytes) -> bytes:
    """Encrypt content using the shared PII key rotation pool."""
    return pii_crypto.encrypt_bytes(content)


def decrypt(content: bytes) -> bytes:
    """Decrypts previously encrypted content and returns the original bytes."""
    return pii_crypto.decrypt_bytes(content)
