import asyncio
import uuid
from collections.abc import Callable
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.mark.integration
def test_ws_connect_me_channel_success(
    client: TestClient,
    access_token_factory: Callable[[str], str],
) -> None:
    user_id = str(uuid.uuid4())
    token = access_token_factory(user_id)
    with client.websocket_connect(f"/ws/me.{user_id}", subprotocols=[f"bearer.{token}"]):
        pass


@pytest.mark.integration
def test_ws_connect_no_token_closes_unauthorized(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/me.some-user") as ws:
            ws.receive_text()
    assert exc_info.value.code == 4401


@pytest.mark.integration
def test_ws_connect_unknown_channel_closes_normal(
    client: TestClient,
    access_token_factory: Callable[[str], str],
) -> None:
    token = access_token_factory("user-1")
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/unknown.channel", subprotocols=[f"bearer.{token}"]
        ) as ws:
            ws.receive_text()
    assert exc_info.value.code == 1000


@pytest.mark.integration
def test_ws_me_channel_forbidden_for_other_user(
    client: TestClient,
    access_token_factory: Callable[[str], str],
) -> None:
    token = access_token_factory("user-a")
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/me.user-b", subprotocols=[f"bearer.{token}"]) as ws:
            ws.receive_text()
    assert exc_info.value.code == 4403


@pytest.mark.integration
def test_ws_entry_channel_with_scanner_token(
    client: TestClient,
    scanner_token_factory: Callable[..., str],
) -> None:
    event_id = uuid.uuid4()
    token = scanner_token_factory(uuid.uuid4(), uuid.uuid4(), event_id)
    with client.websocket_connect(f"/ws/entry.{event_id}", subprotocols=[f"bearer.{token}"]):
        pass


@pytest.mark.integration
def test_ws_entry_channel_denies_access_token(
    client: TestClient,
    access_token_factory: Callable[[str], str],
) -> None:
    event_id = uuid.uuid4()
    token = access_token_factory("user-1")
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/ws/entry.{event_id}", subprotocols=[f"bearer.{token}"]
        ) as ws:
            ws.receive_text()
    assert exc_info.value.code == 4403


@pytest.mark.integration
def test_ws_invalid_token_closes_unauthorized(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/me.user-1", subprotocols=["bearer.not-a-valid-jwt"]
        ) as ws:
            ws.receive_text()
    assert exc_info.value.code == 4401


@pytest.mark.integration
def test_hub_deliver_reaches_subscriber(
    client: TestClient,
    access_token_factory: Callable[[str], str],
) -> None:
    from com.qode.qrew.v1.gateway.hub.hub import get_hub

    user_id = str(uuid.uuid4())
    token = access_token_factory(user_id)
    with client.websocket_connect(f"/ws/me.{user_id}", subprotocols=[f"bearer.{token}"]) as ws:
        hub = get_hub()
        # TestClient's ASGI app runs in a background thread with its own event loop.
        # Use asyncio.run() in the background thread context via run_in_executor isn't
        # available here, so we schedule deliver on the hub's loop directly.
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                hub.deliver(f"me.{user_id}", {"type": "test_event", "data": "hello"})
            )
        finally:
            loop.close()
        msg = ws.receive_json()
        assert msg["type"] == "test_event"
