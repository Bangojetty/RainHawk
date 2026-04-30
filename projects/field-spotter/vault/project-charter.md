# field-spotter — Project Charter

**What it is.** `field-spotter` is a small, self-contained Python toolkit
for analyzing wildlife observation logs. It assumes the user is a
naturalist or citizen scientist who collects timestamped point-sightings
of animals in a fixed local area and wants help reasoning over those
records.

**In scope.**
- A pure-Python core library that operates on lists of `Sighting`
  records (timestamp, location, species, optional distinguishing
  features) and produces analytical outputs: clustering into estimated
  individuals, summarising activity, etc.
- Standard-library only — no external dependencies at runtime.
- A small CLI for invoking analyses against a JSON observation log.

**Out of scope.**
- No camera-trap image processing, no audio classification, no GIS
  integration, no real-time data ingestion.
- No persistent database — input is a JSON file.
- No multi-observer/sensor reconciliation; single observer assumed.

**Project slug:** `field-spotter`. The slug is intentionally generic so
future features (e.g. activity-period summariser, species-co-occurrence
analyser) can be added under the same project as their own per-feature
directories.
