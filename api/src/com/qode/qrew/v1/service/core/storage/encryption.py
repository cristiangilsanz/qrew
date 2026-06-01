from com.qode.qrew.v1.service.core.auth import pii_crypto

ENCRYPTED_KINDS = frozenset({"kyc"})


def should_encrypt(kind: str) -> bool:
    """Return whether a kind must be encrypted at rest."""
    return kind in ENCRYPTED_KINDS


def encrypt(content: bytes) -> bytes:
    """Encrypt content using the shared PII key rotation pool."""
    return pii_crypto.encrypt_bytes(content)


def decrypt(content: bytes) -> bytes:
    """Decrypt content written by encrypt()."""
    return pii_crypto.decrypt_bytes(content)
