"""Pretty-print an Itinerary as a human-readable schedule."""

from __future__ import annotations

from dawn_walker.models import Itinerary
from dawn_walker.timefmt import format_hhmm


def render_itinerary(it: Itinerary) -> str:
    """Render `it` as a multi-line string.

    Format:

        Dawn walk starting at <start_label> (HH:MM)
        ----------------------------------------------------
        HH:MM  walk  N min   ->  <next stop name> (<category>)
        HH:MM  arrive
        HH:MM  depart
        HH:MM  walk  N min   ->  <next stop name> (<category>)
        ...
        HH:MM  end
        Total: <hh>h <mm>m, <N> stops, ~<km> km walked

    Designed to be diff-stable so tests can assert against it.
    """
    if not it.stops:
        return (
            f"Dawn walk starting at {it.start_label} ({format_hhmm(it.start_minute)})\n"
            f"(empty itinerary — no stops scheduled)\n"
        )

    lines = [
        f"Dawn walk starting at {it.start_label} ({format_hhmm(it.start_minute)})",
        "-" * 60,
    ]

    for leg, stop in zip(it.legs, it.stops):
        lines.append(
            f"{format_hhmm(leg.depart_minute)}  walk  {leg.minutes:>3d} min   ->  "
            f"{stop.poi.name} ({stop.poi.category})"
        )
        lines.append(f"{format_hhmm(stop.arrive_minute)}  arrive")
        lines.append(f"{format_hhmm(stop.depart_minute)}  depart")

    end_min = it.stops[-1].depart_minute
    lines.append(f"{format_hhmm(end_min)}  end")

    total_min = end_min - it.start_minute
    hh, mm = divmod(total_min, 60)
    total_walk_min = sum(leg.minutes for leg in it.legs)
    approx_km = (total_walk_min / 60.0) * it.walking_kph
    lines.append(
        f"Total: {hh}h {mm:02d}m, {len(it.stops)} stops, "
        f"~{approx_km:.1f} km walked"
    )
    return "\n".join(lines) + "\n"
