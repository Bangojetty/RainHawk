# Plan — morning-ritual-planner

## Components

1. **Domain model** (`dawn_walker/models.py`) — dataclasses for `POI`, `TimeWindow`, `ItineraryStop`, `Itinerary`. POIs hold a category, lat/lon, dwell-minutes, and open window (in minutes-from-midnight, with optional wrap-around for night-only spots).
2. **Geometry** (`dawn_walker/geo.py`) — `haversine_km(a, b)` great-circle distance and `walking_minutes(a, b, kph)` derived from it.
3. **Planner** (`dawn_walker/planner.py`) — `plan_itinerary(start_point, start_minute, category_sequence, pois, walking_kph)`:
    - For each requested category in sequence, pick the POI of that category that minimizes arrival time given current position and current time, *and* whose open window contains the dwell.
    - If no candidate of a category is feasible, raise `InfeasibleItinerary` with a clear reason (which category, which time, which POIs were considered, why each was rejected).
    - Return an `Itinerary` with one `ItineraryStop` per category plus walking-leg metadata.
4. **Time helpers** (`dawn_walker/timefmt.py`) — minutes-from-midnight ↔ "HH:MM" formatting; window membership respecting wrap-around (e.g. 22:00–04:00).
5. **Renderer** (`dawn_walker/render.py`) — `render_itinerary(itinerary) -> str` produces a printable multi-line schedule.
6. **CLI** (`dawn_walker/__main__.py`) — `python -m dawn_walker plan <pois.json>` loads JSON, runs planner, prints rendered output. JSON contains start, sequence, walking_kph, and pois list.

## Files to create (under `projects/dawn-walker/`)

- `dawn_walker/__init__.py`
- `dawn_walker/__main__.py`
- `dawn_walker/models.py`
- `dawn_walker/geo.py`
- `dawn_walker/timefmt.py`
- `dawn_walker/planner.py`
- `dawn_walker/render.py`
- `tests/__init__.py`
- `tests/test_geo.py`
- `tests/test_timefmt.py`
- `tests/test_planner.py`
- `tests/test_render.py`
- `tests/test_cli.py`
- `examples/hanoi_dawn.json` — a small fixture inspired by the captured sentences (flower market, ceremony, produce market, exercise spot, photo spot, breakfast).
- `pyproject.toml` — minimal config so `pytest` runs cleanly.
- `README.md` — usage in 30 lines or fewer.

## Test strategy

- **Unit:** `geo` (known-distance pairs), `timefmt` (parse/format round-trips, wrap-around membership), `models` (validation), `render` (golden-string assertions).
- **Planner:** at least these cases — happy path (everything fits), category-sequence reordering matters, night-only POI feasibility (window 22:00–04:00 with start 03:30), infeasible-because-closed (clear reason), infeasible-because-arrival-too-late, multiple candidates per category and the planner picks the soonest-feasible.
- **CLI:** load the example JSON, run the entry point, assert success exit code and key strings in stdout.
- All tests must pass via `python -m pytest projects/dawn-walker/tests` (or invoked from the project directory). Target: ~20+ passing tests.

## Acceptance criteria

1. `python -m pytest projects/dawn-walker/tests` exits 0 with all tests passing.
2. `python -m dawn_walker plan projects/dawn-walker/examples/hanoi_dawn.json` (run from `projects/dawn-walker/`) prints a chronological itinerary with arrival/departure times for each requested category and walking-leg minutes between stops.
3. Planner returns a clear, structured `InfeasibleItinerary` with the offending category and reason when no feasible plan exists.
4. No third-party runtime dependencies; standard library only. (pytest is a dev dependency.)
5. `featuresum/dawn-walker__morning-ritual-planner.md` written per the spec.

## Risks / unknowns

- Pytest discovery from a non-package-on-PYTHONPATH location: solve by adding a `conftest.py` that injects `projects/dawn-walker/` into `sys.path`, or by running pytest from inside that directory. I'll go with the latter and document it.
- Wrap-around windows: easy to get off-by-one. Will cover with explicit tests for windows that span midnight and arrivals on either side.
