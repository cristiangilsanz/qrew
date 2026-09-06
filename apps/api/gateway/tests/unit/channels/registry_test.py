# tests registry
import com.qode.qrew.v1.gateway.channels.entry  # noqa: F401
import com.qode.qrew.v1.gateway.channels.me  # noqa: F401
from com.qode.qrew.v1.gateway.channels.registry import ChannelDefinition, resolve


# verifies that resolve me channel
def test_resolve_me_channel() -> None:
    result = resolve("me.abc-123")
    assert result is not None
    definition, params = result
    assert params == {"user_id": "abc-123"}


# verifies that resolve entry channel
def test_resolve_entry_channel() -> None:
    result = resolve("entry.evt-456")
    assert result is not None
    definition, params = result
    assert params == {"event_id": "evt-456"}


# verifies that resolve unknown returns none
def test_resolve_unknown_returns_none() -> None:
    assert resolve("unknown.channel") is None
    assert resolve("payments.x") is None
    assert resolve("") is None


# verifies that resolve partial match returns none
def test_resolve_partial_match_returns_none() -> None:
    assert resolve("me.") is None


# verifies that channel definition match extracts params
def test_channel_definition_match_extracts_params() -> None:
    defn = ChannelDefinition(
        key_pattern="room.{room_id}.seat.{seat_id}",
        can_subscribe=lambda c, p: True,  # type: ignore[arg-type]
        queue_size=64,
    )
    result = defn.match("room.abc.seat.def")
    assert result == {"room_id": "abc", "seat_id": "def"}


# verifies that channel definition match returns none on mismatch
def test_channel_definition_match_returns_none_on_mismatch() -> None:
    defn = ChannelDefinition(
        key_pattern="room.{room_id}",
        can_subscribe=lambda c, p: True,  # type: ignore[arg-type]
        queue_size=64,
    )
    assert defn.match("other.xyz") is None
