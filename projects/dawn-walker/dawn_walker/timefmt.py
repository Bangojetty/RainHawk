"""Time helpers that work in 'minutes since midnight' (ints in [0, 1440)).

We deliberately avoid `datetime` here. Itineraries are anchored to a single
day and the only awkward case is windows that wrap past midnight (e.g. a
flower market open 22:00–04:00). Integer minutes keep that explicit.
"""

from __future__ import annotations

MINUTES_PER_DAY = 24 * 60


def parse_hhmm(s: str) -> int:
    """Parse 'HH:MM' (24-hour) into minutes since midnight.

    Accepts strings like '00:00', '04:30', '23:59'. Raises ValueError on
    malformed input or out-of-range hours/minutes.
    """
    if not isinstance(s, str):
        raise ValueError(f"expected string, got {type(s).__name__}")
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"expected 'HH:MM', got {s!r}")
    hh_s, mm_s = parts
    if not (hh_s.isdigit() and mm_s.isdigit()):
        raise ValueError(f"non-numeric components in {s!r}")
    hh, mm = int(hh_s), int(mm_s)
    if not (0 <= hh <= 23):
        raise ValueError(f"hour out of range in {s!r}")
    if not (0 <= mm <= 59):
        raise ValueError(f"minute out of range in {s!r}")
    return hh * 60 + mm


def format_hhmm(minutes: int) -> str:
    """Format minutes-since-midnight as 'HH:MM'.

    Values >= 1440 wrap (i.e. minute 1500 is 01:00 the next day). Negative
    values are an error.
    """
    if minutes < 0:
        raise ValueError(f"negative minutes not supported: {minutes}")
    m = minutes % MINUTES_PER_DAY
    return f"{m // 60:02d}:{m % 60:02d}"


def in_window(minute: int, start: int, end: int) -> bool:
    """Is `minute` inside the window [start, end)?

    Both `start` and `end` are minutes since midnight (each in [0, 1440)).
    If `start <= end`, the window is the obvious half-open range.
    If `start > end`, the window wraps midnight (e.g. 22:00–04:00 means
    [22:00, 24:00) ∪ [0:00, 04:00)). `start == end` is treated as an empty
    window — it is never feasible.
    """
    minute = minute % MINUTES_PER_DAY
    if start == end:
        return False
    if start < end:
        return start <= minute < end
    # wrap-around
    return minute >= start or minute < end
