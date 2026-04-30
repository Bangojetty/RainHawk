"""Lat/lon distance + walking-time estimates.

Plain great-circle distance (haversine). Good enough for short urban walks;
the planner's whole accuracy budget is dwarfed by the user's choice of
walking-pace constant anyway.
"""

from __future__ import annotations

import math
from typing import Tuple

EARTH_RADIUS_KM = 6371.0088
DEFAULT_WALKING_KPH = 4.5  # comfortable adult walking pace

LatLon = Tuple[float, float]


def haversine_km(a: LatLon, b: LatLon) -> float:
    """Great-circle distance between two (lat, lon) points, in kilometres."""
    lat1, lon1 = a
    lat2, lon2 = b
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
        raise ValueError("latitude must be in [-90, 90]")
    if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError("longitude must be in [-180, 180]")
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def walking_minutes(a: LatLon, b: LatLon, kph: float = DEFAULT_WALKING_KPH) -> int:
    """Estimated walking time between two points, rounded up to whole minutes.

    Rounding up matches a walker's intuition: "if it takes 6 minutes 10
    seconds, plan 7." Distance of zero returns zero, not one.
    """
    if kph <= 0:
        raise ValueError("walking speed must be positive")
    km = haversine_km(a, b)
    if km == 0:
        return 0
    minutes_exact = (km / kph) * 60.0
    return math.ceil(minutes_exact)
