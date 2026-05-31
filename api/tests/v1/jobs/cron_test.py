import pytest

from com.qode.qrew.v1.service.core.jobs.cron import parse_crontab


def test_parse_every_15_minutes() -> None:
    fields = parse_crontab("*/15 * * * *")
    assert fields.minute == {0, 15, 30, 45}
    assert fields.hour is None
    assert fields.day is None


def test_parse_daily_at_3am() -> None:
    fields = parse_crontab("0 3 * * *")
    assert fields.minute == {0}
    assert fields.hour == {3}


def test_parse_range_and_list() -> None:
    fields = parse_crontab("0 9-11,15 * * 1-5")
    assert fields.hour == {9, 10, 11, 15}
    assert fields.weekday == {1, 2, 3, 4, 5}


def test_rejects_wrong_arity() -> None:
    with pytest.raises(ValueError, match="5 fields"):
        parse_crontab("0 3 * *")


def test_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="invalid cron field"):
        parse_crontab("0 25 * * *")
