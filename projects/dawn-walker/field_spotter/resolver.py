"""The cluster-into-individuals algorithm.

Greedy chronological assignment. For each sighting in time order:
  - Compute the set of *candidate* clusters: those whose accumulated
    features are compatible with this sighting AND whose most recent
    sighting is reachable from this one inside the time gap.
  - If exactly one candidate, append.
  - If multiple candidates, pick the one with the smallest cost
    (`time_gap_minutes * (1 + distance_m)`), tie-break by cluster id.
  - If none, open a new cluster.

This greedy approach is intentionally simple: it does not backtrack. For
the input sizes a single observer produces (dozens, not thousands), and
for inputs where features are at least somewhat informative, it
produces sensible partitions. Documented limitation, not a bug.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Iterable, List, Optional, Tuple

from field_spotter.compat import (
    euclidean_m,
    features_compatible_with_individual,
    merge_features,
    reachable,
)
from field_spotter.models import (
    FeatureConflict,
    Individual,
    Resolution,
    Sighting,
)


def _link_cost(latest: Sighting, s: Sighting) -> float:
    """Lower is "more likely the same individual". Combines time gap
    and distance — a near-simultaneous sighting at the same spot has
    cost ~0, distant or long-gap pairs cost more."""
    dt = abs(latest.t_min - s.t_min)
    d = euclidean_m(latest, s)
    return dt * (1.0 + d)


def resolve(
    sightings: Iterable[Sighting],
    max_speed_mps: float,
) -> Resolution:
    """Cluster `sightings` into estimated individuals.

    Parameters
    ----------
    sightings : iterable of Sighting
        The observations to resolve. Order does not matter; the resolver
        sorts by `(t_min, id)` internally for determinism.
    max_speed_mps : float
        The species' plausible top travel speed in metres per second.
        For red foxes a reasonable value is ~13 m/s (sprint) or ~3 m/s
        (sustained); pick what suits the observation timescale.

    Returns
    -------
    Resolution
    """
    if max_speed_mps <= 0:
        raise ValueError("max_speed_mps must be positive")

    items = sorted(list(sightings), key=lambda s: (s.t_min, s.id))
    if not items:
        return Resolution(individuals=[], sighting_to_individual={}, splits=[])

    # Mutable bookkeeping during the sweep.
    clusters: List[Individual] = []
    latest_member: Dict[str, Sighting] = {}  # cluster id -> latest sighting object
    s_to_ind: Dict[str, str] = {}
    splits: List[Tuple[str, str]] = []
    next_idx = 1

    def _new_cluster(seed: Sighting, reason: str) -> Individual:
        nonlocal next_idx
        ind = Individual(
            id=f"I{next_idx:03d}",
            sighting_ids=[seed.id],
            sex=seed.sex,
            age_class=seed.age_class,
            size_class=seed.size_class,
            markings=set(seed.markings),
        )
        next_idx += 1
        clusters.append(ind)
        latest_member[ind.id] = seed
        s_to_ind[seed.id] = ind.id
        splits.append((seed.id, reason))
        return ind

    for s in items:
        # Find compatible candidate clusters.
        candidates: List[Tuple[float, Individual]] = []
        for ind in clusters:
            if not features_compatible_with_individual(s, ind):
                continue
            latest = latest_member[ind.id]
            if not reachable(latest, s, max_speed_mps):
                continue
            cost = _link_cost(latest, s)
            candidates.append((cost, ind))

        if not candidates:
            _new_cluster(s, "first sighting" if not clusters else "no compatible cluster")
            continue

        # Pick best by (cost, cluster id).
        candidates.sort(key=lambda t: (t[0], t[1].id))
        _, chosen = candidates[0]

        try:
            new_sex, new_age, new_size, new_markings = merge_features(s, chosen)
        except FeatureConflict:
            # Compatibility check should have prevented this, but be
            # defensive: open a new cluster.
            _new_cluster(s, "merge raised conflict (defensive)")
            continue

        chosen.sighting_ids.append(s.id)
        chosen.sex = new_sex
        chosen.age_class = new_age
        chosen.size_class = new_size
        chosen.markings = new_markings
        latest_member[chosen.id] = s
        s_to_ind[s.id] = chosen.id

    return Resolution(
        individuals=list(clusters),
        sighting_to_individual=s_to_ind,
        splits=splits,
    )
