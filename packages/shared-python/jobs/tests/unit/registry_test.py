# tests registry
import uuid

import pytest
from jobs.errors import JobNotFoundError
from jobs.registry import JobSpec, all_specs, get_spec, job, parse_crontab, register


# handles unique
def _unique(base: str = "job") -> str:
    return f"{base}_{uuid.uuid4().hex[:8]}"


class TestRegisterAndGet:
    # verifies that register and retrieve
    def test_register_and_retrieve(self) -> None:
        name = _unique()

        # handles handler
        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        spec = get_spec(name)
        assert spec.name == name
        assert spec.handler is handler

    # verifies that get unknown raises
    def test_get_unknown_raises(self) -> None:
        with pytest.raises(JobNotFoundError):
            get_spec("does_not_exist_xyz")

    # verifies that all specs includes registered
    def test_all_specs_includes_registered(self) -> None:
        name = _unique()

        # handles handler
        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        names = [s.name for s in all_specs()]
        assert name in names

    # verifies that default max attempts
    def test_default_max_attempts(self) -> None:
        name = _unique()

        # handles handler
        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        assert get_spec(name).max_attempts == 3

    # verifies that default retry delays
    def test_default_retry_delays(self) -> None:
        name = _unique()

        # handles handler
        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        assert get_spec(name).retry_delays == [30, 120, 600]


class TestJobDecorator:
    # verifies that registers function
    def test_registers_function(self) -> None:
        name = _unique()

        # handles my handler
        @job(name)
        async def my_handler(ctx, payload):
            pass

        spec = get_spec(name)
        assert spec.handler is my_handler

    # verifies that custom max attempts
    def test_custom_max_attempts(self) -> None:
        name = _unique()

        # handles my handler
        @job(name, max_attempts=5)
        async def my_handler(ctx, payload):
            pass

        assert get_spec(name).max_attempts == 5

    # verifies that decorator returns original function
    def test_decorator_returns_original_function(self) -> None:
        name = _unique()

        # handles my handler
        @job(name)
        async def my_handler(ctx, payload):
            pass

        assert callable(my_handler)


class TestParseCrontab:
    # verifies that all wildcards
    def test_all_wildcards(self) -> None:
        fields = parse_crontab("* * * * *")
        assert fields.minute == "*"
        assert fields.hour == "*"
        assert fields.day == "*"
        assert fields.month == "*"
        assert fields.weekday == "*"

    # verifies that numeric fields
    def test_numeric_fields(self) -> None:
        fields = parse_crontab("30 9 * * 1")
        assert fields.minute == 30
        assert fields.hour == 9
        assert fields.weekday == 1

    # verifies that comma separated
    def test_comma_separated(self) -> None:
        fields = parse_crontab("0,30 * * * *")
        assert fields.minute == {0, 30}

    # verifies that wrong field count raises
    def test_wrong_field_count_raises(self) -> None:
        with pytest.raises(ValueError, match="5 cron fields"):
            parse_crontab("* * * *")

    # verifies that six fields raises
    def test_six_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="5 cron fields"):
            parse_crontab("* * * * * *")
