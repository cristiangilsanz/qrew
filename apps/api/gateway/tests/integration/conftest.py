import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from starlette.testclient import TestClient

# Generate keypairs before patching settings
_ec_private = ec.generate_private_key(ec.SECP256R1())
_EC_PRIVATE_PEM = _ec_private.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()

_rsa_private = rsa.generate_private_key(65537, 2048)
_RSA_PRIVATE_PEM = _rsa_private.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()

# Patch settings BEFORE importing app so lifespan doesn't raise
from com.qode.qrew.v1.gateway.core.config import settings  # noqa: E402

settings.debug = True
settings.nats_url = ""
settings.idempotency_enabled = False
settings.jwt_audience = ""
settings.jwt_issuer = ""
settings.ws_heartbeat_seconds = 60
settings.access_jwt_private_key = _EC_PRIVATE_PEM
settings.scanner_jwt_private_key = _RSA_PRIVATE_PEM

from com.qode.qrew.v1.gateway.core.auth import access_public_keys, scanner_public_keys  # noqa: E402

access_public_keys.cache_clear()
scanner_public_keys.cache_clear()

from com.qode.qrew.v1.gateway.app import app  # noqa: E402


@pytest.fixture(scope="session")
def access_token_factory() -> object:
    def _make(user_id: str) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": user_id,
                "type": "access",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
            },
            _EC_PRIVATE_PEM,
            algorithm="ES256",
        )

    return _make


@pytest.fixture(scope="session")
def scanner_token_factory() -> object:
    def _make(scanner_id: uuid.UUID, venue_id: uuid.UUID, event_id: uuid.UUID) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "scanner_id": str(scanner_id),
                "venue_id": str(venue_id),
                "event_id": str(event_id),
                "date": "2026-06-23",
                "type": "scanner",
                "aud": "qrew.scan",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=12)).timestamp()),
            },
            _RSA_PRIVATE_PEM,
            algorithm="RS256",
        )

    return _make


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c  # type: ignore[misc]
