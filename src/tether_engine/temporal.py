"""UTC information bounds; calendar precision is never silently padded to its start."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import re

from .serde import ContractError


_CALENDAR = re.compile(r"([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?")
_INSTANT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                      r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})")


def utc_instant(value: datetime | str) -> datetime:
    """Accept a timezone-aware instant and compare its UTC value, not local date."""
    try:
        if type(value) is str:
            if _INSTANT.fullmatch(value) is None:
                raise ValueError('Unsupported instant syntax')
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError('Timezone is required')
        return value.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as error:
        raise ContractError('Information time requires an explicit timezone-aware ISO instant') from error


def available_by(bound: datetime | str, cutoff: datetime | str) -> bool:
    """Exact upper-bound equality is eligible: information is known by the cutoff."""
    return utc_instant(bound) <= utc_instant(cutoff)


@dataclass(frozen=True)
class CalendarBounds:
    precision: str
    lower: datetime
    latest: datetime


def calendar_bounds(value: date | str | int) -> CalendarBounds:
    """Bounds of a year/month/day at the runtime's microsecond resolution.

    `latest` is the last representable instant of the half-open calendar period,
    not a claim that publication actually happened then. Keep precision with it.
    """
    if type(value) is date:
        value = value.isoformat()
    elif type(value) is int:
        value = f'{value:04d}'
    if type(value) is not str:
        raise ContractError('Calendar time requires an ISO year, month or day')
    match = _CALENDAR.fullmatch(value)
    if match is None:
        raise ContractError('Calendar time requires an ISO year, month or day')
    try:
        year = int(match[1])
        month = int(match[2]) if match[2] else None
        day = int(match[3]) if match[3] else None
        lower = date(year, month or 1, day or 1)
        end_month = month if month is not None else 12
        end_day = day if day is not None else monthrange(year, end_month)[1]
        latest = date(year, end_month, end_day)
    except (ValueError, OverflowError) as error:
        raise ContractError('Invalid calendar time') from error
    return CalendarBounds('day' if day is not None else 'month' if month is not None else 'year',
                          datetime.combine(lower, time.min, timezone.utc),
                          datetime.combine(latest, time.max, timezone.utc))
