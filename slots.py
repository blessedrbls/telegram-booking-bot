"""Calculating free time slots. No Telegram code here, only dates and times."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from config import BOOKING_DAYS_AHEAD, DATETIME_FORMAT, SLOT_STEP_MINUTES, TIMEZONE


def now_local() -> datetime:
    """Current time in Kyiv.

    tzinfo is removed so it can be compared with times from the database,
    which are also stored as Kyiv time without a timezone.
    """
    return datetime.now(TIMEZONE).replace(tzinfo=None)


def upcoming_days() -> List[date]:
    """Today and the next days (7 days in total by default)."""
    today = now_local().date()
    return [today + timedelta(days=i) for i in range(BOOKING_DAYS_AHEAD)]


def to_datetime(text: str) -> datetime:
    """'2026-11-10 14:30' -> datetime object."""
    return datetime.strptime(text, DATETIME_FORMAT)


def combine(day: date, hhmm: str) -> datetime:
    """date(2026, 11, 10) + '14:30' -> datetime(2026, 11, 10, 14, 30)."""
    return datetime.combine(day, datetime.strptime(hhmm, "%H:%M").time())


def get_free_slots(
    day: date,
    work_start: str,
    work_end: str,
    duration: int,
    busy: List[Tuple[datetime, datetime]],
    now: Optional[datetime] = None,
) -> List[str]:
    """Return free start times for one day, e.g. ['10:00', '10:30', ...].

    day        - the date we check
    work_start - master's start of work, '10:00'
    work_end   - master's end of work, '20:00'
    duration   - service length in minutes
    busy       - list of (start, end) of existing bookings of this master
    now        - current time (can be passed in tests)
    """
    if now is None:
        now = now_local()

    step = timedelta(minutes=SLOT_STEP_MINUTES)
    length = timedelta(minutes=duration)

    slot_start = combine(day, work_start)
    day_end = combine(day, work_end)

    free = []
    # The service must END before the master finishes work
    while slot_start + length <= day_end:
        slot_end = slot_start + length

        is_past = slot_start <= now

        # Two time ranges overlap if each one starts before the other ends
        is_busy = any(
            slot_start < busy_end and slot_end > busy_start
            for busy_start, busy_end in busy
        )

        if not is_past and not is_busy:
            free.append(slot_start.strftime("%H:%M"))

        slot_start += step

    return free
