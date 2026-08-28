# tests channels
import pytest

from com.qode.qrew.v1.gateway.channels.entry import can_subscribe_entry
from com.qode.qrew.v1.gateway.channels.me import can_subscribe_me


# verifies that me allows owner
@pytest.mark.asyncio
async def test_me_allows_owner() -> None:
    user_id = "user-abc"
    claims: dict[str, object] = {"sub": user_id, "type": "access"}
    params = {"user_id": user_id}
    assert await can_subscribe_me(claims, params) is True


# verifies that me denies other user
@pytest.mark.asyncio
async def test_me_denies_other_user() -> None:
    claims: dict[str, object] = {"sub": "user-abc", "type": "access"}
    params = {"user_id": "user-xyz"}
    assert await can_subscribe_me(claims, params) is False


# verifies that me denies missing sub
@pytest.mark.asyncio
async def test_me_denies_missing_sub() -> None:
    claims: dict[str, object] = {"type": "access"}
    params = {"user_id": "user-abc"}
    assert await can_subscribe_me(claims, params) is False


# verifies that entry allows scanner token
@pytest.mark.asyncio
async def test_entry_allows_scanner_token() -> None:
    claims: dict[str, object] = {"type": "scanner", "scanner_id": "sc-1"}
    params = {"event_id": "evt-1"}
    assert await can_subscribe_entry(claims, params) is True


# verifies that entry denies access token
@pytest.mark.asyncio
async def test_entry_denies_access_token() -> None:
    claims: dict[str, object] = {"type": "access", "sub": "user-1"}
    params = {"event_id": "evt-1"}
    assert await can_subscribe_entry(claims, params) is False


# verifies that entry denies missing type
@pytest.mark.asyncio
async def test_entry_denies_missing_type() -> None:
    claims: dict[str, object] = {"sub": "user-1"}
    params = {"event_id": "evt-1"}
    assert await can_subscribe_entry(claims, params) is False
