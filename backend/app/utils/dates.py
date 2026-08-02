from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def day_bounds(value: date) -> tuple[datetime, datetime]:
    start = datetime.combine(value, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def as_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
