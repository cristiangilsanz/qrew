import uuid

import pytest
from jobs.errors import JobNotFoundError
from jobs.registry import JobSpec, all_specs, get_spec, job, parse_crontab, register


def _unique(base: str = "job") -> str:
    return f"{base}_{uuid.uuid4().hex[:8]}"


class TestRegisterAndGet:
    def test_register_and_retrieve(self) -> None:
        name = _unique()

        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        spec = get_spec(name)
        assert spec.name == name
        assert spec.handler is handler

    def test_get_unknown_raises(self) -> None:
        with pytest.raises(JobNotFoundError):
            get_spec("does_not_exist_xyz")

    def test_all_specs_includes_registered(self) -> None:
        name = _unique()

        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        names = [s.name for s in all_specs()]
        assert name in names

    def test_default_max_attempts(self) -> None:
        name = _unique()

        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        assert get_spec(name).max_attempts == 3

    def test_default_retry_delays(self) -> None:
        name = _unique()

        async def handler(ctx, payload):
            pass

        register(JobSpec(name=name, handler=handler))
        assert get_spec(name).retry_delays == [30, 120, 600]


class TestJobDecorator:
    def test_registers_function(self) -> None:
        name = _unique()

        @job(name)
        async def my_handler(ctx, payload):
            pass

        spec = get_spec(name)
        assert spec.handler is my_handler

    def test_custom_max_attempts(self) -> None:
        name = _unique()

        @job(name, max_attempts=5)
        async def my_handler(ctx, payload):
            pass

        assert get_spec(name).max_attempts == 5

    def test_decorator_returns_original_function(self) -> None:
        name = _unique()

        @job(name)
        async def my_handler(ctx, payload):
            pass

        assert callable(my_handler)


class TestParseCrontab:
    def test_all_wildcards(self) -> None:
        fields = parse_crontab("* * * * *")
        assert fields.minute == "*"
        assert fields.hour == "*"
        assert fields.day == "*"
        assert fields.month == "*"
        assert fields.weekday == "*"

    def test_numeric_fields(self) -> None:
        fields = parse_crontab("30 9 * * 1")
        assert fields.minute == 30
        assert fields.hour == 9
        assert fields.weekday == 1

    def test_comma_separated(self) -> None:
        fields = parse_crontab("0,30 * * * *")
        assert fields.minute == {0, 30}

    def test_wrong_field_count_raises(self) -> None:
        with pytest.raises(ValueError, match="5 cron fields"):
            parse_crontab("* * * *")

    def test_six_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="5 cron fields"):
            parse_crontab("* * * * * *")
