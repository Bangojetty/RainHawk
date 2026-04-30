# dawn-walker — morning-ritual-planner

First feature on a brand-new project. Random-web-inspiration strategy, v1.

## Random query

> the quiet rituals of small market towns at dawn

Invented as a freely associated sentence. No topical bias intended; it
ended up adjacent to dawn / market / ritual themes, which is what shaped
the feature.

## Source URL

Picked from the WebSearch results: **IZITOUR — *Hanoi's Dawn: Markets,
Traditions, and Morning Rituals*** —
https://izitour.com/en/hanoi-dawn-markets-traditions-morning-rituals.
Picked because it was the closest semantic match that wasn't fiction or a
generic listicle, and travel-tour writeups tend to enumerate concrete
activities with timing and place.

## Captured sentences (from across the article)

1. "Stroll between the shops that are full of colorful flowers come from different places."
2. "This is the biggest flower market in the city and is open at night time only."
3. "This solemn ceremony happens every morning but still attracts many people."
4. "Everything here is fresh: green vegetables, meats, noodles, even live chickens, ducks and fish."
5. "This is one of very few traditional open door markets that still exist in the city center."
6. "joining Tai Chi, aerobic morning exercises or laughing yoga at the Ly Thai To Statue park."
7. "Take some amazing photos of the lake, even capture some pictures of parents carrying their kids on motorbikes to school."
8. "Head to the Old Quarter for a typical breakfast with a bowl of Pho and some iced coffee."
9. "Settled in the over a thousand of years old city, Hanoian have a typical Asian style when their days start very early."
10. "Remember bring your full charged camera"

## Synthesized feature idea

A planner that takes a starting point, a starting clock time, an ordered
list of "ritual" categories (e.g. *flower-market → ceremony →
produce-market → exercise → photo → breakfast*), and a pool of candidate
POIs (each with a category, location, dwell time, and open-time window),
and produces a feasible chronological itinerary. It must respect
wrap-around windows (the "open at night time only" flower market),
walking times between stops, and waiting when the walker arrives before
a window opens. When no plan is possible, it raises a structured
`InfeasibleItinerary` with per-candidate diagnostics.

## What I actually built

A single Python package, `dawn_walker`, under
`projects/dawn-walker/`. Standard library only.

```
projects/dawn-walker/
├── dawn_walker/
│   ├── __init__.py        # re-exports
│   ├── __main__.py        # CLI: `python -m dawn_walker plan <pois.json>`
│   ├── geo.py             # haversine + walking_minutes
│   ├── timefmt.py         # HH:MM <-> minutes-since-midnight, in_window
│   ├── models.py          # POI, TimeWindow, Itinerary, InfeasibleItinerary
│   ├── planner.py         # greedy-by-sequence-position algorithm
│   └── render.py          # human-readable schedule string
├── examples/hanoi_dawn.json   # the integration fixture (and the demo)
├── tests/                 # 63 passing tests across 6 files
├── pyproject.toml
└── morning-ritual-planner/    # the per-feature directory (notes only)
    ├── inspiration.md
    ├── feature-idea.md
    ├── plan.md
    └── problem-log.md
```

Project-wide notes live in `projects/dawn-walker/vault/project-charter.md`.

### Key design choices

- **Integer minutes-since-midnight, not `datetime`.** A dawn walk lives in
  one calendar day; the only awkward case is a window that wraps past
  midnight. Modelling that with ints + a single "wrap if close < open"
  rule was cleaner than fighting timezones.
- **Greedy, not optimal.** The planner picks the soonest-departing
  feasible candidate per category in sequence order. For 3–6 morning
  stops this produces sensible plans and stays trivial to reason about.
  A future feature could swap in DP if needed.
- **Diagnostics on the failure path.** `InfeasibleItinerary` carries the
  offending category and a `attempts` dict naming each rejected POI and
  why — much more useful than a generic "no plan found".
- **Standard library only.** Easier to reproduce, no dependency
  resolution, no version drift.

## Test results

`python -m pytest tests` → **63 passed, 0 failed** (≈0.05s wall clock).

| File | Tests | Covers |
|---|---|---|
| `test_timefmt.py` | 15 | parse/format round-trip, wrap-around windows |
| `test_geo.py` | 10 | haversine known-distance pairs, ceil rounding, validation |
| `test_models.py` | 13 | POI / TimeWindow validation, exception payload |
| `test_planner.py` | 15 | happy path, waiting, wrap-around, infeasibility, candidate selection, no-reuse, input validation |
| `test_render.py` | 4 | header, ordering, walking minutes, empty case |
| `test_cli.py` | 6 | example fixture, exit codes, infeasible flag, missing file |

## Retrospective

**What went well.**
- Tracing the example by hand before relying on it caught an infeasible
  fixture (flower-market window 22:00–04:30 with a 30-min dwell after a
  ~59-min walk) before I'd written a single test. Saved a debugging
  loop. Logged in `problem-log.md`.
- The planner passed all 63 tests on first run. The "minutes since
  midnight + wrap rule" abstraction did exactly the work it promised.
- Greedy-by-sequence is enough for this scope. Resisted the pull to
  build a DP / branch-and-bound thing.

**What was hard.**
- Two encoding bugs at the Windows console boundary (Unicode `→` arrow,
  then em-dashes inside user data). The first was a my-fault choice of
  glyph; the second required rethinking *where* the encoding boundary is
  — at I/O, not at the data layer. Fix: a `_safe_write` helper in
  `__main__` that re-encodes through stdout's encoding with `errors=
  "replace"`. Both incidents in `problem-log.md`.
- The wrap-around window math has a small but real off-by-one risk
  around `close == arrive + dwell`. The half-open window convention
  (close is exclusive) made it tractable but I had to write explicit
  tests on both sides of every boundary to convince myself.

**What I'd do differently next time.**
- Default to ASCII for any visible glyph in CLI output from the start.
  Pretty Unicode is a portability tax, not free.
- Run the CLI against the bundled example *before* claiming green —
  pytest goes through the rendered string, not through stdout, so it
  doesn't catch console-encoding bugs.
- Consider adding a `--json` flag from day one so the output is
  machine-readable for downstream tools. Cheap and avoids future
  rework.
- Write a tiny golden-text test for the rendered example end-to-end
  (after stripping volatile fields), so any regression in the layout
  shows up loudly.
