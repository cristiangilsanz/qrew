from typing import Any

import pytest

from com.qode.qrew.v1.service.core.jobs import registry
from com.qode.qrew.v1.service.core.jobs.registry import (
    DEFAULT_RETRY_DELAYS_SECONDS,
    all_specs,
    get_spec,
    job,
    reset_registry_for_tests,
)


async def _noop(ctx: dict[str, Any]) -> None:
    del ctx


@pytest.fixture
def isolated_registry() -> Any:
    snapshot = {spec.name: spec for spec in all_specs()}
    reset_registry_for_tests()
    yield
    reset_registry_for_tests()
    for name, spec in snapshot.items():
        registry._REGISTRY[name] = spec  # pyright: ignore[reportPrivateUsage]


def test_decorator_registers_handler(isolated_registry: Any) -> None:
    del isolated_registry
    job(name="test.simple")(_noop)
    spec = get_spec("test.simple")
    assert spec.handler is _noop
    assert spec.max_attempts == 5
    assert spec.cron_fields is None


def test_decorator_parses_cron(isolated_registry: Any) -> None:
    del isolated_registry
    job(name="test.cron", cron="0 3 * * *")(_noop)
    spec = get_spec("test.cron")
    assert spec.cron_fields is not None
    assert spec.cron_fields.hour == {3}
    assert spec.cron_fields.minute == {0}


def test_duplicate_name_rejected(isolated_registry: Any) -> None:
    del isolated_registry
    job(name="test.dup")(_noop)
    with pytest.raises(ValueError, match="duplicate"):
        job(name="test.dup")(_noop)


def test_retry_delays_must_cover_attempts(isolated_registry: Any) -> None:
    del isolated_registry
    with pytest.raises(ValueError, match="retry_delays"):
        job(name="test.bad_retry", max_attempts=5, retry_delays=(1, 2))(_noop)


def test_default_retry_delays_cover_five_attempts() -> None:
    assert len(DEFAULT_RETRY_DELAYS_SECONDS) >= 4
