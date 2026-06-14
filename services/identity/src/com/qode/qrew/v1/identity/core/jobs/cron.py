from dataclasses import dataclass

_CRONTAB_FIELDS = 5


@dataclass(frozen=True)
class CronFields:
    minute: set[int] | None
    hour: set[int] | None
    day: set[int] | None
    month: set[int] | None
    weekday: set[int] | None


_RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "weekday": (0, 6),
}


def _parse_field(raw: str, name: str) -> set[int] | None:
    low, high = _RANGES[name]
    if raw == "*":
        return None
    out: set[int] = set()
    for part in raw.split(","):
        step = 1
        body = part
        if "/" in part:
            body, step_raw = part.split("/", 1)
            step = int(step_raw)
        if body == "*":
            start, end = low, high
        elif "-" in body:
            start_raw, end_raw = body.split("-", 1)
            start, end = int(start_raw), int(end_raw)
        else:
            start = end = int(body)
        if start < low or end > high or start > end or step < 1:
            raise ValueError(f"invalid cron field for {name}: {raw}")
        out.update(range(start, end + 1, step))
    return out


def parse_crontab(expr: str) -> CronFields:
    parts = expr.split()
    if len(parts) != _CRONTAB_FIELDS:
        raise ValueError(f"crontab must have 5 fields, got {len(parts)}: {expr!r}")
    minute, hour, day, month, weekday = parts
    return CronFields(
        minute=_parse_field(minute, "minute"),
        hour=_parse_field(hour, "hour"),
        day=_parse_field(day, "day"),
        month=_parse_field(month, "month"),
        weekday=_parse_field(weekday, "weekday"),
    )
