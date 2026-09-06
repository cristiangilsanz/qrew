# tests notify
import asyncio
import importlib
import inspect
import uuid
from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from outbox import notify
from outbox.notify import PENDING_KEY, install_drain_notifier, mark_pending
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session

REDIS_URL = "redis://localhost:6379/0"


# stands in for sqlalchemy's event module, noting every listener the notifier wires
class _Recorder:
    def __init__(self, wired: list[tuple[Any, str, Any]]) -> None:
        self.wired = wired

    # registers the listener for real and remembers it, so the test can unwire it
    def listens_for(self, target: Any, identifier: str, **kw: Any) -> Any:
        real = event.listens_for(target, identifier, **kw)

        # notes the listener before handing it to sqlalchemy
        def decorate(fn: Any) -> Any:
            self.wired.append((target, identifier, fn))
            return real(fn)

        return decorate


# builds a throwaway database, so a commit reaches a real transaction
@pytest.fixture
def engine() -> Iterator[Engine]:
    made = create_engine("sqlite://")
    yield made
    made.dispose()


# opens a session on the throwaway database
@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    opened = Session(engine)
    yield opened
    opened.close()


# installs a notifier under a unique name and unwires it once the test is done
@pytest.fixture
def install() -> Iterator[Callable[..., str]]:
    added: list[tuple[Any, str, Any]] = []

    # wires a notifier and remembers the listeners it registered
    def _install(**kwargs: Any) -> str:
        name = f"svc_{uuid.uuid4().hex[:8]}"
        install_drain_notifier(name, redis_url=REDIS_URL, **kwargs)
        return name

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(notify, "event", _Recorder(added))
        yield _install
    for target, identifier, fn in added:
        event.remove(target, identifier, fn)
    notify._installed.clear()  # pyright: ignore[reportPrivateUsage]


# lets every notification scheduled so far finish before the test asserts on it
async def _settle() -> None:
    while notify._tasks:  # pyright: ignore[reportPrivateUsage]
        await asyncio.gather(*list(notify._tasks))  # pyright: ignore[reportPrivateUsage]


# replaces the enqueue the notifier reaches for with a spy
@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    called = AsyncMock(return_value=None)
    monkeypatch.setattr("jobs.enqueue", called)
    return called


class TestMarkPending:
    # verifies that a marked session carries the flag
    def test_marks_the_session(self, session: Session) -> None:
        mark_pending(session)
        assert session.info[PENDING_KEY] is True

    # verifies that a session without info is left alone
    def test_session_without_info_does_not_raise(self) -> None:
        class Bare:
            pass

        mark_pending(Bare())

    # verifies that a non mapping info is left alone
    def test_non_mapping_info_does_not_raise(self) -> None:
        class Odd:
            info = "not a mapping"

        mark_pending(Odd())
        assert Odd.info == "not a mapping"


class TestNotifyOnCommit:
    # verifies that the notice goes out only once the transaction commits
    async def test_notifies_after_commit(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        name = install()
        session.execute(text("select 1"))
        mark_pending(session)
        assert spy.await_count == 0
        session.commit()
        await _settle()
        spy.assert_awaited_once()
        assert spy.await_args is not None
        assert spy.await_args.args[0] == f"{name}.outbox.drain"
        assert spy.await_args.kwargs["queue_name"] == f"qrew:jobs:{name}"

    # verifies that nothing is scheduled while the transaction is still open
    async def test_nothing_before_commit(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        install()
        session.execute(text("select 1"))
        mark_pending(session)
        await _settle()
        assert spy.await_count == 0

    # verifies that an unmarked commit wakes nobody
    async def test_unmarked_commit_is_silent(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        install()
        session.execute(text("select 1"))
        session.commit()
        await _settle()
        assert spy.await_count == 0

    # verifies that the mark is spent, so a second commit does not notify again
    async def test_mark_is_consumed(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        install()
        session.execute(text("select 1"))
        mark_pending(session)
        session.commit()
        session.execute(text("select 1"))
        session.commit()
        await _settle()
        assert spy.await_count == 1

    # verifies that an explicit job name overrides the derived one
    async def test_explicit_job_name(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        name = install(job_name="identity.event_outbox.drain")
        session.execute(text("select 1"))
        mark_pending(session)
        session.commit()
        await _settle()
        assert spy.await_args is not None
        assert spy.await_args.args[0] == "identity.event_outbox.drain"
        assert spy.await_args.kwargs["queue_name"] == f"qrew:jobs:{name}"

    # verifies that wiring the same drainer twice does not double the notice
    async def test_second_install_does_not_double_wire(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        name = install()
        install_drain_notifier(name, redis_url=REDIS_URL)
        session.execute(text("select 1"))
        mark_pending(session)
        session.commit()
        await _settle()
        assert spy.await_count == 1


class TestRollback:
    # verifies that a rolled back transaction wakes nobody
    async def test_rollback_drops_the_mark(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        install()
        session.execute(text("select 1"))
        mark_pending(session)
        session.rollback()
        assert PENDING_KEY not in session.info
        session.execute(text("select 1"))
        session.commit()
        await _settle()
        assert spy.await_count == 0

    # verifies that a rollback before any database work drops the mark too
    async def test_soft_rollback_drops_the_mark(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        install()
        session.begin()
        mark_pending(session)
        session.rollback()
        assert PENDING_KEY not in session.info
        session.execute(text("select 1"))
        session.commit()
        await _settle()
        assert spy.await_count == 0


class TestFailuresAreSwallowed:
    # verifies that a broken enqueue never reaches the caller, the cron covers it
    async def test_enqueue_failure_does_not_propagate(
        self,
        session: Session,
        install: Callable[..., str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        boom = AsyncMock(side_effect=TypeError("takes 1 positional argument but 2"))
        monkeypatch.setattr("jobs.enqueue", boom)
        install()
        session.execute(text("select 1"))
        mark_pending(session)
        session.commit()
        await _settle()
        boom.assert_awaited_once()

    # verifies that a commit outside a loop warns instead of blowing up
    def test_commit_without_a_running_loop(
        self, session: Session, install: Callable[..., str], spy: AsyncMock
    ) -> None:
        install()
        session.execute(text("select 1"))
        mark_pending(session)
        session.commit()
        assert spy.await_count == 0


class TestEnqueueSignature:
    # verifies that what enqueue sends is what a drainer accepts
    async def test_enqueued_call_binds_to_the_drainer(
        self,
        session: Session,
        install: Callable[..., str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from jobs import JobSpec, register

        # stands in for a service drainer, with the signature the real ones declare
        async def drain_outbox(
            ctx: dict[str, Any], payload: dict[str, Any] | None = None
        ) -> dict[str, int]:
            del ctx, payload
            return {"sent": 0}

        name = install()
        job_name = f"{name}.outbox.drain"
        register(JobSpec(name=job_name, handler=drain_outbox))

        sent: dict[str, Any] = {}

        # records the call arq would hand to the worker
        async def enqueue_job(function: str, *args: Any, **kwargs: Any) -> None:
            sent["function"] = function
            sent["args"] = args
            sent["kwargs"] = kwargs

        pool = AsyncMock()
        pool.enqueue_job = enqueue_job
        module = importlib.import_module("jobs.enqueue")
        monkeypatch.setattr(module, "get_pool", AsyncMock(return_value=pool))

        session.execute(text("select 1"))
        mark_pending(session)
        session.commit()
        await _settle()

        assert sent["function"] == job_name
        # arq replays the stored arguments after the context, so the drainer must
        # accept the body enqueue passes positionally
        inspect.signature(drain_outbox).bind({}, *sent["args"])
        assert sent["args"] == ({},)
        assert sent["kwargs"]["_queue_name"] == f"qrew:jobs:{name}"
