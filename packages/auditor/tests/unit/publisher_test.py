from unittest.mock import AsyncMock, MagicMock, patch

from auditor.publisher import publish_audit_event

_PATCH_NATS = "messaging.client.get_nats"
_PATCH_ENVELOPE = "contracts.messaging.envelope.EventEnvelope"


class TestPublishAuditEvent:
    async def test_publishes_to_nats(self) -> None:
        mock_nc = MagicMock()
        mock_nc.js = MagicMock()
        mock_nc.js.publish = AsyncMock()

        mock_envelope_instance = MagicMock()
        mock_envelope_instance.model_dump_json = MagicMock(return_value='{"ok":true}')
        MockEnvelope = MagicMock(return_value=mock_envelope_instance)

        with (
            patch(_PATCH_NATS, return_value=mock_nc),
            patch(_PATCH_ENVELOPE, MockEnvelope),
        ):
            await publish_audit_event(
                subject="audit.events.v1",
                aggregate_type="user",
                aggregate_id="user-123",
                actor_id="actor-456",
                data={"action": "login"},
            )

        mock_nc.js.publish.assert_awaited_once()
        subject_arg = mock_nc.js.publish.call_args.args[0]
        assert subject_arg == "audit.events.v1"

    async def test_nats_unavailable_is_swallowed(self) -> None:
        with patch(_PATCH_NATS, side_effect=RuntimeError("nats down")):
            await publish_audit_event(
                subject="audit.events.v1",
                aggregate_type="user",
                aggregate_id="u1",
                actor_id=None,
                data={},
            )

    async def test_publish_error_is_swallowed(self) -> None:
        mock_nc = MagicMock()
        mock_nc.js = MagicMock()
        mock_nc.js.publish = AsyncMock(side_effect=RuntimeError("publish failed"))

        mock_envelope_instance = MagicMock()
        mock_envelope_instance.model_dump_json = MagicMock(return_value="{}")
        MockEnvelope = MagicMock(return_value=mock_envelope_instance)

        with (
            patch(_PATCH_NATS, return_value=mock_nc),
            patch(_PATCH_ENVELOPE, MockEnvelope),
        ):
            await publish_audit_event(
                subject="audit.events.v1",
                aggregate_type="system",
                aggregate_id="sys",
                actor_id=None,
                data={},
            )
