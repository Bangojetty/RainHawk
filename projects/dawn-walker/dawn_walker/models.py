"""Domain model: POIs, time windows, itineraries.

All times are minutes-since-midnight ints. Locations are (lat, lon) tuples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from dawn_walker.timefmt import format_hhmm, in_window


LatLon = Tuple[float, float]


class InfeasibleItinerary(Exception):
    """Raised by `plan_itinerary` when no feasible plan exists.

    Attributes:
        category: the category whose stop could not be scheduled.
        reason:   human-readable summary of why each candidate failed.
        attempts: per-candidate notes (POI name → reason) for diagnostics.
    """

    def __init__(self, category: str, reason: str, attempts: dict[str, str]):
        super().__init__(f"infeasible at category {category!r}: {reason}")
        self.category = category
        self.reason = reason
        self.attempts = attempts


@dataclass(frozen=True)
class TimeWindow:
    """A half-open time window [open_minute, close_minute).

    `close_minute < open_minute` means the window wraps midnight. Values
    must be in [0, 1440).
    """

    open_minute: int
    close_minute: int

    def __post_init__(self) -> None:
        for name, v in (("open_minute", self.open_minute),
                        ("close_minute", self.close_minute)):
            if not isinstance(v, int):
                raise TypeError(f"{name} must be int")
            if not (0 <= v < 24 * 60):
                raise ValueError(f"{name} out of range [0, 1440): {v}")
        if self.open_minute == self.close_minute:
            raise ValueError("empty time window (open == close)")

    def contains(self, minute: int) -> bool:
        return in_window(minute, self.open_minute, self.close_minute)

    def __str__(self) -> str:
        return f"{format_hhmm(self.open_minute)}–{format_hhmm(self.close_minute)}"


@dataclass(frozen=True)
class POI:
    """A point of interest the walker may visit.

    `dwell_minutes` is the time the walker stays once they arrive. A visit
    is feasible iff both arrival and (arrival + dwell) — i.e. the moment
    just before departure — fall inside `window`. Wrap-around windows are
    allowed, but the dwell itself may not span the closed segment.
    """

    name: str
    category: str
    location: LatLon
    dwell_minutes: int
    window: TimeWindow

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("POI.name is required")
        if not self.category:
            raise ValueError("POI.category is required")
        if self.dwell_minutes < 0:
            raise ValueError("dwell_minutes must be non-negative")
        lat, lon = self.location
        if not (-90 <= lat <= 90):
            raise ValueError(f"latitude out of range: {lat}")
        if not (-180 <= lon <= 180):
            raise ValueError(f"longitude out of range: {lon}")


@dataclass(frozen=True)
class WalkingLeg:
    """A walking segment between two consecutive scheduled stops (or from
    the trip's starting point to the first stop)."""

    from_label: str
    to_label: str
    minutes: int
    depart_minute: int
    arrive_minute: int


@dataclass(frozen=True)
class ItineraryStop:
    poi: POI
    arrive_minute: int
    depart_minute: int

    @property
    def category(self) -> str:
        return self.poi.category


@dataclass(frozen=True)
class Itinerary:
    start_label: str
    start_location: LatLon
    start_minute: int
    stops: List[ItineraryStop] = field(default_factory=list)
    legs: List[WalkingLeg] = field(default_factory=list)
    walking_kph: float = 4.5

    @property
    def end_minute(self) -> int:
        return self.stops[-1].depart_minute if self.stops else self.start_minute
