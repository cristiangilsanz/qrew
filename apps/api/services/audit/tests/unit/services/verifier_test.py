from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

from com.qode.qrew.v1.audit.models.event import AuditEvent
from com.qode.qrew.v1.audit.services.verifier import AuditChainVerifier

_PATCH_SESSION = "com.qode.qrew.v1.audit.services.verifier.AsyncSessionLocal"
_PATCH_REPO = "com.qode.qrew.v1.audit.services.verifier.AuditRepository"


def _mock_verifier(events: list[AuditEvent]) -> AuditChainVerifier:
    mock_session = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(_PATCH_SESSION, return_value=mock_cm),
        patch(_PATCH_REPO) as mock_repo_cls,
    ):
        mock_repo_cls.return_value.get_all_ordered = AsyncMock(return_value=events)
        return AuditChainVerifier(), mock_cm, mock_repo_cls


async def _verify(events: list[AuditEvent]):  # type: ignore[no-untyped-def]
    mock_session = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(_PATCH_SESSION, return_value=mock_cm),
        patch(_PATCH_REPO) as mock_repo_cls,
    ):
        mock_repo_cls.return_value.get_all_ordered = AsyncMock(return_value=events)
        return await AuditChainVerifier().verify()


async def test_empty_chain_is_valid() -> None:
    result = await _verify([])

    assert result.valid is True
    assert result.event_count == 0
    assert result.tampered_ids == []


async def test_single_event_chain_is_valid(
    make_chain: Callable[[int], list[AuditEvent]],
) -> None:
    result = await _verify(make_chain(1))

    assert result.valid is True
    assert result.event_count == 1
    assert result.tampered_ids == []


async def test_multi_event_chain_is_valid(
    make_chain: Callable[[int], list[AuditEvent]],
) -> None:
    result = await _verify(make_chain(5))

    assert result.valid is True
    assert result.event_count == 5
    assert result.tampered_ids == []


async def test_tampered_last_event_detected(
    make_chain: Callable[[int], list[AuditEvent]],
) -> None:
    events = make_chain(3)
    events[-1].hash = b"\x00" * 32

    result = await _verify(events)

    assert result.valid is False
    assert str(events[-1].id) in result.tampered_ids
    assert len(result.tampered_ids) == 1


async def test_tampered_event_cascades_to_downstream(
    make_chain: Callable[[int], list[AuditEvent]],
) -> None:
    # Corrupting events[1] breaks its own hash check and event[2]'s prev_hash,
    # so both are reported.
    events = make_chain(3)
    events[1].hash = b"\x00" * 32

    result = await _verify(events)

    assert result.valid is False
    assert str(events[1].id) in result.tampered_ids
    assert str(events[2].id) in result.tampered_ids
    assert len(result.tampered_ids) == 2


async def test_tampered_event_count_still_reflects_total(
    make_chain: Callable[[int], list[AuditEvent]],
) -> None:
    events = make_chain(3)
    events[0].hash = b"\x00" * 32

    result = await _verify(events)

    assert result.event_count == 3


async def test_last_event_tampered(
    make_chain: Callable[[int], list[AuditEvent]],
) -> None:
    events = make_chain(3)
    events[-1].hash = b"\x00" * 32

    result = await _verify(events)

    assert result.valid is False
    assert str(events[-1].id) in result.tampered_ids
