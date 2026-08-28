# tests outbox drainer
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestDrainOutbox:
    # verifies that drain empty outbox returns zero
    async def test_drain_empty_outbox_returns_zero(self, setup_test_infrastructure) -> None:
        from com.qode.qrew.v1.identity.worker.jobs.outbox_drainer import drain_outbox

        result = await drain_outbox({})
        assert result["drained"] == 0

    # verifies that drain returns int
    async def test_drain_returns_int(self, setup_test_infrastructure) -> None:
        from com.qode.qrew.v1.identity.worker.jobs.outbox_drainer import drain_outbox

        result = await drain_outbox({})
        assert isinstance(result["drained"], int)
