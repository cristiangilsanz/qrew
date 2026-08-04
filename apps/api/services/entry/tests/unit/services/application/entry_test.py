import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from conftest import make_scanner, make_ticket_ctx

from com.qode.qrew.v1.entry.models.projections import TicketState
from com.qode.qrew.v1.entry.services.application.entry.entry import validate_entry
from com.qode.qrew.v1.entry.services.domain.entry import EntryReason

_MOD = "com.qode.qrew.v1.entry.services.application.entry.entry"

_PATCH_JWT = f"{_MOD}.jwt"
_PATCH_JWT_KEYS = f"{_MOD}.jwt_keys"
_PATCH_SETTINGS = f"{_MOD}.settings"
_PATCH_TC_REPO = f"{_MOD}.TicketContextRepository"
_PATCH_ATTEMPT_REPO = f"{_MOD}.EntryAttemptRepository"
_PATCH_REDLOCK = f"{_MOD}.redlock"
_PATCH_TICKETING = f"{_MOD}._call_ticketing_use"


def _make_redis(*, set_result: object = True) -> MagicMock:
    redis = MagicMock()
    redis.set = AsyncMock(return_value=set_result)
    return redis


def _make_fake_settings() -> MagicMock:
    s = MagicMock()
    s.ticket_qr_audience = "qrew.ticket"
    s.entry_replay_grace_seconds = 30
    s.redis_url = "redis://localhost:6379"
    return s


def _make_redlock_cm() -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _make_jwt_mocks(
    *,
    kid: str = "kid1",
    payload: dict | None = None,
    decode_side_effect: Exception | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Return (mock_jwt, mock_jwt_keys) configured for the given scenario."""
    mock_jwt = MagicMock()
    mock_jwt.get_unverified_header = MagicMock(return_value={"kid": kid})
    mock_jwt.ExpiredSignatureError = jwt.ExpiredSignatureError
    mock_jwt.InvalidAudienceError = jwt.InvalidAudienceError
    mock_jwt.InvalidTokenError = jwt.InvalidTokenError

    if decode_side_effect is not None:
        mock_jwt.decode = MagicMock(side_effect=decode_side_effect)
    else:
        mock_jwt.decode = MagicMock(return_value=payload or {})

    mock_jwt_keys = MagicMock()
    mock_jwt_keys.TICKET_QR = "ticket_qr"
    mock_jwt_keys.get_verifiers = MagicMock(
        return_value={kid: "-----BEGIN PUBLIC KEY-----\nfake\n"}
    )

    return mock_jwt, mock_jwt_keys


def _valid_payload(
    *,
    ticket_id: uuid.UUID,
    event_id: uuid.UUID,
    venue_id: uuid.UUID,
    jti: str = "jti-abc",
    exp: int | None = None,
) -> dict:
    if exp is None:
        exp = int(datetime.now(UTC).timestamp()) + 300
    return {
        "ticket_id": str(ticket_id),
        "event_id": str(event_id),
        "venue_id": str(venue_id),
        "jti": jti,
        "exp": exp,
    }


async def _run(
    *,
    ticket_jwt: str = "fake.jwt.token",
    scanner: SimpleNamespace | None = None,
    scanner_event_id: uuid.UUID | None = None,
    scanner_venue_id: uuid.UUID | None = None,
    redis: MagicMock | None = None,
    audit: AsyncMock | None = None,
    mock_jwt: MagicMock | None = None,
    mock_jwt_keys: MagicMock | None = None,
    tc_repo_result: object = None,
    settings: MagicMock | None = None,
    redlock_cm: MagicMock | None = None,
    ticketing_side_effect: Exception | None = None,
):
    from com.qode.qrew.v1.entry.services.application.audit import AuditService

    if scanner is None:
        scanner = make_scanner(venue_id=scanner_venue_id or uuid.uuid4())
    if scanner_venue_id is None:
        scanner_venue_id = scanner.venue_id
    if redis is None:
        redis = _make_redis()
    if audit is None:
        audit = AsyncMock(spec=AuditService)
        audit.record = AsyncMock()
    if mock_jwt is None or mock_jwt_keys is None:
        mock_jwt, mock_jwt_keys = _make_jwt_mocks()
    if settings is None:
        settings = _make_fake_settings()

    mock_tc_repo = MagicMock()
    mock_tc_repo.return_value.get = AsyncMock(return_value=tc_repo_result)

    mock_attempt_repo = MagicMock()
    mock_attempt_repo.return_value.record = AsyncMock()

    mock_redlock = redlock_cm or _make_redlock_cm()
    mock_ticketing = AsyncMock(side_effect=ticketing_side_effect)

    db_session = MagicMock()

    with (
        patch(_PATCH_JWT, mock_jwt),
        patch(_PATCH_JWT_KEYS, mock_jwt_keys),
        patch(_PATCH_SETTINGS, settings),
        patch(_PATCH_TC_REPO, mock_tc_repo),
        patch(_PATCH_ATTEMPT_REPO, mock_attempt_repo),
        patch(_PATCH_REDLOCK, return_value=mock_redlock),
        patch(_PATCH_TICKETING, mock_ticketing),
    ):
        return await validate_entry(
            db_session,
            redis,
            ticket_jwt=ticket_jwt,
            scanner=scanner,
            scanner_event_id=scanner_event_id,
            scanner_venue_id=scanner_venue_id,
            audit=audit,
        )


class TestValidateEntryJwtErrors:
    async def test_denied_when_kid_not_in_verifiers(self) -> None:
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(kid="kid1")
        mock_jwt_keys.get_verifiers = MagicMock(return_value={})  # no matching kid
        outcome = await _run(mock_jwt=mock_jwt, mock_jwt_keys=mock_jwt_keys)
        assert not outcome.allowed
        assert outcome.reason == EntryReason.signature

    async def test_denied_when_jwt_expired(self) -> None:
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            decode_side_effect=jwt.ExpiredSignatureError("expired")
        )
        outcome = await _run(mock_jwt=mock_jwt, mock_jwt_keys=mock_jwt_keys)
        assert not outcome.allowed
        assert outcome.reason == EntryReason.expired

    async def test_denied_when_invalid_audience(self) -> None:
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            decode_side_effect=jwt.InvalidAudienceError("bad audience")
        )
        outcome = await _run(mock_jwt=mock_jwt, mock_jwt_keys=mock_jwt_keys)
        assert not outcome.allowed
        assert outcome.reason == EntryReason.audience

    async def test_denied_when_invalid_signature(self) -> None:
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            decode_side_effect=jwt.InvalidTokenError("bad sig")
        )
        outcome = await _run(mock_jwt=mock_jwt, mock_jwt_keys=mock_jwt_keys)
        assert not outcome.allowed
        assert outcome.reason == EntryReason.signature

    async def test_denied_when_payload_missing_required_fields(self) -> None:
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(payload={"ticket_id": "only-this"})
        outcome = await _run(mock_jwt=mock_jwt, mock_jwt_keys=mock_jwt_keys)
        assert not outcome.allowed
        assert outcome.reason == EntryReason.signature

    async def test_denied_when_payload_uuids_are_invalid(self) -> None:
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload={
                "ticket_id": "not-a-uuid",
                "event_id": "not-a-uuid",
                "venue_id": "not-a-uuid",
                "jti": "jti-abc",
                "exp": 9999999999,
            }
        )
        outcome = await _run(mock_jwt=mock_jwt, mock_jwt_keys=mock_jwt_keys)
        assert not outcome.allowed
        assert outcome.reason == EntryReason.signature


class TestValidateEntryContextChecks:
    async def test_denied_when_wrong_event(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        other_event = uuid.uuid4()
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=other_event,  # different from JWT event_id
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.wrong_event

    async def test_denied_when_wrong_venue(self, event_id: uuid.UUID) -> None:
        ticket_id = uuid.uuid4()
        venue_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        other_venue = uuid.uuid4()
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=other_venue),
            scanner_venue_id=other_venue,  # different from JWT venue_id
            scanner_event_id=event_id,
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.wrong_venue

    async def test_denied_when_replay(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        redis = _make_redis(set_result=None)  # None = key existed, nx=True rejected
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            redis=redis,
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.replay

    async def test_denied_when_ticket_not_found(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            tc_repo_result=None,
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.not_found

    async def test_denied_when_ticket_belongs_to_wrong_event(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        # ticket context has a different event_id than the JWT
        tc = make_ticket_ctx(ticket_id=ticket_id, event_id=uuid.uuid4())
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            tc_repo_result=tc,
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.wrong_owner

    async def test_denied_when_ticket_state_is_used(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        tc = make_ticket_ctx(
            ticket_id=ticket_id, event_id=event_id, state=TicketState.redeemed.value
        )
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            tc_repo_result=tc,
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.state

    async def test_denied_when_lock_unavailable(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        from locking import LockUnavailableError

        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        tc = make_ticket_ctx(ticket_id=ticket_id, event_id=event_id)
        busy_lock = MagicMock()
        busy_lock.__aenter__ = AsyncMock(side_effect=LockUnavailableError("busy"))
        busy_lock.__aexit__ = AsyncMock(return_value=None)
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            tc_repo_result=tc,
            redlock_cm=busy_lock,
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.busy

    async def test_denied_when_ticketing_call_fails(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        from com.qode.qrew.v1.entry.services.application.entry.entry import (
            _TicketingError,
        )

        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        tc = make_ticket_ctx(ticket_id=ticket_id, event_id=event_id)
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            tc_repo_result=tc,
            ticketing_side_effect=_TicketingError("503"),
        )
        assert not outcome.allowed
        assert outcome.reason == EntryReason.busy


class TestValidateEntryHappyPath:
    async def test_allowed_when_all_checks_pass(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        ticket_id = uuid.uuid4()
        owner = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        tc = make_ticket_ctx(
            ticket_id=ticket_id, event_id=event_id, owner_user_id=owner
        )
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            tc_repo_result=tc,
        )
        assert outcome.allowed
        assert outcome.reason is None
        assert outcome.ticket_id == ticket_id
        assert outcome.holder_user_id == owner

    async def test_allowed_when_no_scanner_event_id(self, venue_id: uuid.UUID) -> None:
        ticket_id = uuid.uuid4()
        event_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        tc = make_ticket_ctx(ticket_id=ticket_id, event_id=event_id)
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=None,  # scanner not assigned to a specific event
            tc_repo_result=tc,
        )
        assert outcome.allowed

    async def test_entry_pending_state_is_allowed(
        self, event_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        ticket_id = uuid.uuid4()
        mock_jwt, mock_jwt_keys = _make_jwt_mocks(
            payload=_valid_payload(
                ticket_id=ticket_id, event_id=event_id, venue_id=venue_id
            )
        )
        tc = make_ticket_ctx(
            ticket_id=ticket_id,
            event_id=event_id,
            state=TicketState.scanning.value,
        )
        outcome = await _run(
            mock_jwt=mock_jwt,
            mock_jwt_keys=mock_jwt_keys,
            scanner=make_scanner(venue_id=venue_id),
            scanner_venue_id=venue_id,
            scanner_event_id=event_id,
            tc_repo_result=tc,
        )
        assert outcome.allowed
