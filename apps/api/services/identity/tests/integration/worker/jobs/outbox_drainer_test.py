import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestDrainOutbox:
    async def test_drain_empty_outbox_returns_zero(self, setup_test_infrastructure) -> None:
        from com.qode.qrew.v1.identity.worker.jobs.outbox_drainer import drain_outbox

        result = await drain_outbox({})
        assert result["drained"] == 0

    async def test_drain_returns_int(self, setup_test_infrastructure) -> None:
        from com.qode.qrew.v1.identity.worker.jobs.outbox_drainer import drain_outbox

        result = await drain_outbox({})
        assert isinstance(result["drained"], int)
