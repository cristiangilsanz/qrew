# wraps the shared nats connection and jetstream context used by every service
from __future__ import annotations

import nats
import nats.js
import structlog
from nats.aio.client import Client

logger = structlog.get_logger(__name__)

_client: Client | None = None


class NatsClient:
    # stores the connection url the client connects to
    def __init__(self, url: str) -> None:
        self._url = url
        self._nc: Client | None = None
        self._js: nats.js.JetStreamContext | None = None

    # connects to nats and opens its jetstream context
    async def connect(self) -> None:
        self._nc = await nats.connect(self._url)  # type: ignore[misc]
        self._js = self._nc.jetstream()  # type: ignore[misc]
        await logger.ainfo("nats.connected", url=self._url)

    # drains and closes the nats connection
    async def close(self) -> None:
        if self._nc is not None:
            try:
                await self._nc.drain()
            except Exception as exc:
                await logger.awarning("nats.drain_failed", error=repr(exc))
            await logger.ainfo("nats.disconnected")

    # returns the connected jetstream context
    @property
    def js(self) -> nats.js.JetStreamContext:
        if self._js is None:
            raise RuntimeError("NATS client not connected")
        return self._js

    # returns the connected nats client
    @property
    def nc(self) -> Client:
        if self._nc is None:
            raise RuntimeError("NATS client not connected")
        return self._nc


_instance: NatsClient | None = None


# returns the shared nats client
def get_nats() -> NatsClient:
    if _instance is None:
        raise RuntimeError("NATS client not initialised — call init_nats() at startup")
    return _instance


# creates and connects the shared nats client
async def init_nats(url: str) -> NatsClient:
    global _instance
    _instance = NatsClient(url)
    await _instance.connect()
    return _instance


# closes and clears the shared nats client
async def close_nats() -> None:
    global _instance
    if _instance is not None:
        await _instance.close()
        _instance = None
