# dawn-walker — Project Charter

**What it is.** `dawn-walker` is a small, self-contained Python application that helps a single walker plan a dawn-to-mid-morning route through a city's "ritual" points-of-interest — markets, exercise spots, photo viewpoints, breakfast spots — respecting each spot's open-time window and the walking distance between them.

**In scope.**
- A pure-Python core library that takes a list of POIs (each with a category, location, opening window, and dwell duration) and a desired ritual sequence, and produces a chronological itinerary.
- Walking-time estimation between POIs (great-circle distance + walking-pace assumption).
- Validation that each scheduled visit fits inside that POI's open window.
- A small command-line entry point that loads POIs from a JSON file and prints an itinerary.

**Out of scope.**
- No real-time map APIs, no road-network routing, no transit, no mobile UI.
- No multi-day planning, no group coordination, no booking.
- No persistent storage beyond input JSON files.

**Project slug:** `dawn-walker`. The slug is intentionally generic so future features (e.g. a dusk variant, a multi-walker scheduler, an export-to-ical formatter) can be added under the same project as their own per-feature directories.
