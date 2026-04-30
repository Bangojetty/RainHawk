"""The itinerary planner.

Given a starting point, a starting clock time, an ordered list of category
labels (e.g. ['flower-market', 'ceremony', 'breakfast']), and a pool of
candidate POIs, build an itinerary that visits one POI per requested
category in the requested order, respecting open windows and walking
times.

Strategy: greedy by sequence position. At each step, among all unused
candidates of the next requested category, pick the one that yields the
soonest *departure* time (so the next leg starts as early as possible).
This is a heuristic — for short morning sequences (3–6 stops) and the
typical case where category memberships don't overlap heavily, it is
both fast and produces sensible plans.

The planner allows a 24-hour look-ahead horizon. Beyond that, it gives up
and raises `InfeasibleItinerary` with diagnostics.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from dawn_walker.geo import walking_minutes
from dawn_walker.models import (
    POI,
    Itinerary,
    ItineraryStop,
    InfeasibleItinerary,
    TimeWindow,
    WalkingLeg,
)
from dawn_walker.timefmt import format_hhmm, MINUTES_PER_DAY


LatLon = Tuple[float, float]
HORIZON_MINUTES = 24 * 60  # one full day of look-ahead


def _dwell_fits(arrive_minute: int, dwell: int, window: TimeWindow) -> bool:
    """Does staying `dwell` minutes starting at `arrive_minute` (absolute)
    keep the walker inside `window` the whole time?

    Treats `arrive_minute` modulo 1440. For dwell == 0 we just check the
    arrival is inside the window.
    """
    if dwell < 0:
        raise ValueError("dwell must be non-negative")
    a = arrive_minute % MINUTES_PER_DAY
    o, c = window.open_minute, window.close_minute
    if dwell == 0:
        return window.contains(a)
    if o < c:
        return o <= a and a + dwell <= c
    # wrap-around window: [o, 1440) ∪ [0, c)
    if a >= o:
        return a + dwell <= c + MINUTES_PER_DAY
    if a < c:
        return a + dwell <= c
    return False


def _earliest_feasible_arrival(
    earliest_minute: int, dwell: int, window: TimeWindow
) -> Optional[int]:
    """Smallest absolute minute >= earliest_minute such that arriving then
    and staying `dwell` minutes fits inside `window`. Searches the next 24
    hours; returns None if no such minute exists in that horizon.
    """
    # Candidate 1: arrive at `earliest_minute` itself.
    if window.contains(earliest_minute) and _dwell_fits(earliest_minute, dwell, window):
        return earliest_minute

    # Candidate 2: wait until the next window opening at or after earliest_minute.
    day = earliest_minute // MINUTES_PER_DAY
    next_open = day * MINUTES_PER_DAY + window.open_minute
    if next_open < earliest_minute:
        next_open += MINUTES_PER_DAY
    # Up to 24h of look-ahead — we try the next one and the one after.
    for candidate in (next_open, next_open + MINUTES_PER_DAY):
        if candidate - earliest_minute > HORIZON_MINUTES:
            break
        if _dwell_fits(candidate, dwell, window):
            return candidate
    return None


def _evaluate_candidate(
    poi: POI,
    current_pos: LatLon,
    current_minute: int,
    walking_kph: float,
) -> Tuple[Optional[int], Optional[int], int, str]:
    """Return (arrive_minute, depart_minute, walk_minutes, reason).

    On success, arrive_minute and depart_minute are non-None and reason is
    "ok". On failure they are None and reason explains why (closed at
    arrival, dwell would overrun close, etc.).
    """
    walk = walking_minutes(current_pos, poi.location, walking_kph)
    earliest = current_minute + walk
    arrive = _earliest_feasible_arrival(earliest, poi.dwell_minutes, poi.window)
    if arrive is None:
        reason = (
            f"earliest possible arrival {format_hhmm(earliest)} cannot fit "
            f"a {poi.dwell_minutes}-minute dwell inside window {poi.window} "
            f"within 24h"
        )
        return None, None, walk, reason
    depart = arrive + poi.dwell_minutes
    return arrive, depart, walk, "ok"


def plan_itinerary(
    start_label: str,
    start_location: LatLon,
    start_minute: int,
    category_sequence: Iterable[str],
    pois: Iterable[POI],
    walking_kph: float = 4.5,
) -> Itinerary:
    """Build a feasible itinerary or raise InfeasibleItinerary.

    Parameters
    ----------
    start_label : str
        Free-text label for the starting point ("Hotel", "Hostel lobby", …).
    start_location : (lat, lon)
        Starting coordinates.
    start_minute : int
        Clock time the walker leaves the starting point, minutes-since-midnight.
    category_sequence : iterable of str
        Categories the walker wants to hit, in order.
    pois : iterable of POI
        Candidate POIs to choose from. Each POI is used at most once.
    walking_kph : float
        Walking pace.

    Returns
    -------
    Itinerary
    """
    if walking_kph <= 0:
        raise ValueError("walking_kph must be positive")
    seq = list(category_sequence)
    if not seq:
        raise ValueError("category_sequence must contain at least one category")
    if not (0 <= start_minute < MINUTES_PER_DAY):
        raise ValueError("start_minute must be in [0, 1440)")

    pool = list(pois)
    used: set[int] = set()  # ids of consumed POIs

    current_pos = start_location
    current_minute = start_minute
    current_label = start_label

    stops: List[ItineraryStop] = []
    legs: List[WalkingLeg] = []

    for category in seq:
        candidates = [
            p for i, p in enumerate(pool)
            if id(p) not in used and p.category == category
        ]
        if not candidates:
            raise InfeasibleItinerary(
                category=category,
                reason=f"no POI of category {category!r} in candidate pool",
                attempts={},
            )

        evaluated = []
        attempts: dict[str, str] = {}
        for poi in candidates:
            arrive, depart, walk, reason = _evaluate_candidate(
                poi, current_pos, current_minute, walking_kph
            )
            if arrive is None or depart is None:
                attempts[poi.name] = reason
            else:
                evaluated.append((depart, arrive, walk, poi))
                attempts[poi.name] = (
                    f"arrive {format_hhmm(arrive)}, depart {format_hhmm(depart)}"
                )

        if not evaluated:
            raise InfeasibleItinerary(
                category=category,
                reason=(
                    f"every candidate of category {category!r} failed; see "
                    f"attempts for per-POI reasons"
                ),
                attempts=attempts,
            )

        # Pick soonest departure; tie-break by arrival, then by POI name for determinism.
        evaluated.sort(key=lambda t: (t[0], t[1], t[3].name))
        depart, arrive, walk, chosen = evaluated[0]

        legs.append(
            WalkingLeg(
                from_label=current_label,
                to_label=chosen.name,
                minutes=walk,
                depart_minute=current_minute,
                arrive_minute=current_minute + walk,
            )
        )
        stops.append(
            ItineraryStop(poi=chosen, arrive_minute=arrive, depart_minute=depart)
        )

        used.add(id(chosen))
        current_pos = chosen.location
        current_minute = depart
        current_label = chosen.name

    return Itinerary(
        start_label=start_label,
        start_location=start_location,
        start_minute=start_minute,
        stops=stops,
        legs=legs,
        walking_kph=walking_kph,
    )
