"""CLI entry point: `python -m dawn_walker plan <pois.json>`.

The JSON file looks like:

    {
        "start": {
            "label": "Hostel",
            "lat": 21.0285,
            "lon": 105.8542,
            "time": "03:30"
        },
        "walking_kph": 4.5,
        "sequence": ["flower-market", "exercise", "breakfast"],
        "pois": [
            {
                "name": "Quang Ba Flower Market",
                "category": "flower-market",
                "lat": 21.0626,
                "lon": 105.8225,
                "dwell": 30,
                "open": "22:00",
                "close": "04:00"
            },
            ...
        ]
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Sequence

from dawn_walker.models import POI, TimeWindow, InfeasibleItinerary
from dawn_walker.planner import plan_itinerary
from dawn_walker.render import render_itinerary
from dawn_walker.timefmt import parse_hhmm


def _poi_from_dict(d: dict) -> POI:
    return POI(
        name=d["name"],
        category=d["category"],
        location=(float(d["lat"]), float(d["lon"])),
        dwell_minutes=int(d["dwell"]),
        window=TimeWindow(
            open_minute=parse_hhmm(d["open"]),
            close_minute=parse_hhmm(d["close"]),
        ),
    )


def run_plan(path: Path) -> str:
    """Load JSON at `path`, plan, and return the rendered itinerary string.

    Raises `InfeasibleItinerary` (which the CLI catches and prints).
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    start = raw["start"]
    pois = [_poi_from_dict(p) for p in raw["pois"]]
    itinerary = plan_itinerary(
        start_label=start["label"],
        start_location=(float(start["lat"]), float(start["lon"])),
        start_minute=parse_hhmm(start["time"]),
        category_sequence=raw["sequence"],
        pois=pois,
        walking_kph=float(raw.get("walking_kph", 4.5)),
    )
    return render_itinerary(itinerary)


def _safe_write(stream, text: str) -> None:
    """Write `text` to `stream` even if the stream's encoding (e.g. cp1252
    on Windows) cannot represent some characters. We replace any unencodable
    characters rather than crash."""
    enc = getattr(stream, "encoding", None) or "utf-8"
    encoded = text.encode(enc, errors="replace").decode(enc, errors="replace")
    stream.write(encoded)


def main(argv: Sequence[str] | None = None) -> int:
    args: List[str] = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != "plan":
        _safe_write(sys.stderr, "usage: python -m dawn_walker plan <pois.json>\n")
        return 2
    path = Path(args[1])
    if not path.exists():
        _safe_write(sys.stderr, f"file not found: {path}\n")
        return 2
    try:
        out = run_plan(path)
    except InfeasibleItinerary as e:
        _safe_write(sys.stderr, f"infeasible: {e}\n")
        for name, reason in e.attempts.items():
            _safe_write(sys.stderr, f"  - {name}: {reason}\n")
        return 1
    _safe_write(sys.stdout, out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
