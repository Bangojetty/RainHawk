"""Pairwise compatibility primitives.

Two sightings (or a sighting and a cluster) are "the same individual"
if and only if:
  1. their distinguishing features don't conflict, AND
  2. the spatial distance between them is reachable in the time gap at
     the species' max plausible speed.

These functions are deliberately small and pure — they make the
resolver's logic testable in isolation.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Optional, Set, Tuple

from field_spotter.models import (
    FeatureConflict,
    Individual,
    Sighting,
)


def _scalar_compatible(a, b) -> bool:
    """Two optional scalar features are compatible iff at least one is
    None or they are equal."""
    if a is None or b is None:
        return True
    return a == b


def _scalar_merge(attr: str, a, b):
    """Pick the more specific of two scalar features, or raise."""
    if a is None:
        return b
    if b is None:
        return a
    if a == b:
        return a
    raise FeatureConflict(attr, a, b)


def _markings_compatible(a: Set[str] | frozenset[str], b: Set[str] | frozenset[str]) -> bool:
    """Two markings sets are compatible iff at least one is empty
    (= unrecorded) or they share at least one marking. Disjoint
    non-empty sets conflict — different animal."""
    a, b = set(a), set(b)
    if not a or not b:
        return True
    return bool(a & b)


def _markings_merge(a: Set[str] | frozenset[str], b: Set[str] | frozenset[str]) -> Set[str]:
    """Union when at least one is empty; intersection-or-raise otherwise.

    Why intersection? Two records of "this individual" should agree on
    the markings actually seen on it; the *set of confirmed markings*
    grows by union *only* when one observer didn't record anything. If
    both observers recorded different non-empty sets of markings on the
    same animal, they're describing different animals — conflict.
    """
    a, b = set(a), set(b)
    if not a:
        return set(b)
    if not b:
        return set(a)
    inter = a & b
    if not inter:
        raise FeatureConflict("markings", sorted(a), sorted(b))
    # Tighten to the agreed-upon subset. (We don't union — the
    # "extra" markings in either set are unverified by the other.)
    return inter


def features_compatible(a: Sighting, b: Sighting) -> bool:
    """Quick check: could `a` and `b` be the same individual ignoring
    space and time?"""
    if not _scalar_compatible(a.sex, b.sex):
        return False
    if not _scalar_compatible(a.age_class, b.age_class):
        return False
    if not _scalar_compatible(a.size_class, b.size_class):
        return False
    if not _markings_compatible(a.markings, b.markings):
        return False
    return True


def features_compatible_with_individual(s: Sighting, ind: Individual) -> bool:
    """Same idea, against an Individual (cluster of accumulated features)."""
    if not _scalar_compatible(s.sex, ind.sex):
        return False
    if not _scalar_compatible(s.age_class, ind.age_class):
        return False
    if not _scalar_compatible(s.size_class, ind.size_class):
        return False
    if not _markings_compatible(s.markings, ind.markings):
        return False
    return True


def merge_features(s: Sighting, ind: Individual) -> Tuple[
    Optional[str], Optional[str], Optional[str], Set[str]
]:
    """Return the (sex, age, size, markings) the cluster would have
    after absorbing `s`. Raises FeatureConflict if not compatible.
    """
    sex = _scalar_merge("sex", s.sex, ind.sex)
    age = _scalar_merge("age_class", s.age_class, ind.age_class)
    size = _scalar_merge("size_class", s.size_class, ind.size_class)
    markings = _markings_merge(s.markings, ind.markings)
    return sex, age, size, markings


def euclidean_m(a: Sighting, b: Sighting) -> float:
    return math.hypot(a.x_m - b.x_m, a.y_m - b.y_m)


def reachable(a: Sighting, b: Sighting, max_speed_mps: float) -> bool:
    """Is the straight-line distance between `a` and `b` reachable by
    something moving at no more than `max_speed_mps` metres per second
    in the time gap between them? Time gap of zero is reachable iff the
    distance is also zero."""
    if max_speed_mps <= 0:
        raise ValueError("max_speed_mps must be positive")
    dt_min = abs(a.t_min - b.t_min)
    dt_s = dt_min * 60.0
    d_m = euclidean_m(a, b)
    if dt_s == 0:
        # Two simultaneous sightings can be the same animal only if
        # they're co-located.
        return d_m == 0
    return d_m <= max_speed_mps * dt_s
