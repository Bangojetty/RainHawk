# Plan — sighting-resolver

## Components

1. **Domain model** (`field_spotter/models.py`) — dataclasses for
   `Sighting` (id, timestamp_minutes, x_m, y_m, sex, age_class,
   size_class, markings_set), `Individual` (id, sighting_ids, merged
   features), `Resolution` (individuals list, sighting→individual map,
   diagnostics).
2. **Compatibility** (`field_spotter/compat.py`) — pairwise functions:
   `features_compatible(a, b)` (no conflicts on shared distinguishing
   features); `temporally_spatially_reachable(a, b, max_speed_mps)` (the
   straight-line distance is reachable in the time gap). Plus
   `merge_features(a, b)` which intersects/unions the feature sets to
   produce a tighter constraint for the cluster.
3. **Resolver** (`field_spotter/resolver.py`) — `resolve(sightings,
   max_speed_mps, link_radius_m=None)`:
    - Sort sightings by timestamp.
    - Process each sighting in order. For each existing cluster, check
      if the sighting is compatible with **the cluster's accumulated
      feature constraints** AND reachable from **the cluster's most
      recent member** in the time-gap.
    - If exactly one cluster matches, append. If multiple match, pick
      the one with the smallest "cost" (time gap × distance, with feature
      specificity as tie-breaker). If none match, start a new cluster.
    - Return a `Resolution` with per-cluster confidence (proxied by the
      number of distinguishing features present and the count of internal
      links).
4. **Diagnostics** (`field_spotter/explain.py`) — `explain(resolution)`
   produces a human-readable summary string: estimated count, each
   individual's feature signature, sighting timeline. Useful for tests
   and the CLI.
5. **CLI** (`field_spotter/__main__.py`) — `python -m field_spotter
   resolve <log.json>` loads a JSON file, runs the resolver, prints the
   explanation.
6. **Examples** (`examples/garden_foxes.json`) — a small fixture
   inspired by the captured sentences: a few overnight observations in a
   garden with two adults (one dog-fox, one vixen) and a handful of
   cubs.

## Files to create (under `projects/field-spotter/`)

- `field_spotter/__init__.py`
- `field_spotter/__main__.py`
- `field_spotter/models.py`
- `field_spotter/compat.py`
- `field_spotter/resolver.py`
- `field_spotter/explain.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_models.py`
- `tests/test_compat.py`
- `tests/test_resolver.py`
- `tests/test_explain.py`
- `tests/test_cli.py`
- `examples/garden_foxes.json`
- `pyproject.toml`

## Test strategy

- **Unit:** `compat` (feature compatibility on sex/age_class/markings,
  with `None` meaning "unknown"; reachability with zero-time, exact-bound,
  too-fast cases); `models` (validation, frozen dataclass behaviour).
- **Resolver:** at least these cases —
  - Single sighting → one individual.
  - Two close-in-time, close-in-space, no conflicting features → one
    individual.
  - Two simultaneous sightings far apart → two individuals.
  - Two sightings far apart in time and space, max-speed makes them
    impossible to be the same → two individuals.
  - Conflicting sex/age-class → forced into separate clusters.
  - "Two vixens, two dog-foxes" pattern: 4 sightings overlapping in
    space but distinguishable by sex+markings → 2 individuals.
  - Tie-breaking: when multiple clusters compatible, picks the one with
    the smaller time-distance cost.
  - Determinism: same input → same output (sighting IDs, individual IDs).
- **Explain:** golden-string assertions over the rendered summary for a
  fixed fixture.
- **CLI:** load the example, run the entry point, assert exit 0 and
  expected substrings.
- All tests via `python -m pytest tests` from the project directory.
  Target: 30+ passing tests.

## Acceptance criteria

1. `python -m pytest tests` exits 0 with all tests passing.
2. `python -m field_spotter resolve examples/garden_foxes.json` (run from
   `projects/field-spotter/`) prints the resolution: number of estimated
   individuals, per-individual features, sighting timeline.
3. The resolver's output is **deterministic** for a given input (same
   IDs, same partition).
4. No third-party runtime dependencies.
5. `featuresum/field-spotter__sighting-resolver.md` written per the
   spec.

## Risks / unknowns

- **Tie-breaking rules can flip the partition.** Two equally-good
  clusters for a sighting and the wrong choice cascades. Mitigation:
  define a clear total ordering (smallest time-cost, then distance, then
  cluster id) and test it.
- **"Unknown" feature semantics.** A sighting with `sex=None` is
  *compatible with anything*; that's the right default but it can lead
  to spurious merges. The resolver only merges when temporally and
  spatially compatible *and* features don't conflict, so the risk is
  bounded but worth a few targeted tests.
