"""CLI entry point: `python -m field_spotter resolve <log.json>`.

The JSON file looks like:

    {
        "max_speed_mps": 13.0,
        "sightings": [
            {"id": "s1", "t_min": 0, "x": 0.0, "y": 0.0,
             "sex": "male", "age": "adult", "size": "medium",
             "markings": ["white-tail-tip"]},
            ...
        ]
    }

Unknown fields are ignored. Missing optional fields default to None or
empty.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Sequence

from field_spotter.explain import explain
from field_spotter.models import Sighting
from field_spotter.resolver import resolve


def _sighting_from_dict(d: dict) -> Sighting:
    return Sighting(
        id=str(d["id"]),
        t_min=int(d["t_min"]),
        x_m=float(d["x"]),
        y_m=float(d["y"]),
        sex=d.get("sex"),
        age_class=d.get("age"),
        size_class=d.get("size"),
        markings=frozenset(d.get("markings") or []),
    )


def run_resolve(path: Path) -> str:
    raw = json.loads(path.read_text(encoding="utf-8"))
    max_speed = float(raw.get("max_speed_mps", 13.0))
    sightings = [_sighting_from_dict(d) for d in raw.get("sightings", [])]
    res = resolve(sightings, max_speed_mps=max_speed)
    return explain(res, sightings=sightings)


def _safe_write(stream, text: str) -> None:
    """Write `text` to `stream` even if the stream's encoding (e.g.
    cp1252 on Windows) cannot represent some characters."""
    enc = getattr(stream, "encoding", None) or "utf-8"
    encoded = text.encode(enc, errors="replace").decode(enc, errors="replace")
    stream.write(encoded)


def main(argv: Sequence[str] | None = None) -> int:
    args: List[str] = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != "resolve":
        _safe_write(sys.stderr, "usage: python -m field_spotter resolve <log.json>\n")
        return 2
    path = Path(args[1])
    if not path.exists():
        _safe_write(sys.stderr, f"file not found: {path}\n")
        return 2
    try:
        out = run_resolve(path)
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        _safe_write(sys.stderr, f"input error: {e}\n")
        return 2
    _safe_write(sys.stdout, out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
