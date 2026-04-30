"""Domain model: Sighting, Individual, Resolution, plus exceptions.

Conventions:
- Time is integer minutes since an arbitrary epoch (the first sighting's
  zero point is fine; only deltas matter for the resolver).
- Position is planar metres in a local tangent plane (x, y). For an
  urban garden / small park, treating lat/lon as flat is fine; the user
  can pre-project if they care.
- "Unknown" feature values are represented by `None`. Two sightings
  whose values disagree (both non-None and unequal) conflict; one None
  and one value is compatible.
- Sets of markings are open-ended strings. Two sets conflict iff they
  are both non-empty and disjoint — i.e. no overlap. Empty set means
  "no markings recorded" (equivalent to None).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


VALID_SEX = {"male", "female"}
VALID_AGE = {"cub", "juvenile", "adult"}
VALID_SIZE = {"small", "medium", "large"}


class FeatureConflict(Exception):
    """Raised by `merge_features` when two feature sets cannot coexist
    in the same individual."""

    def __init__(self, attr: str, a, b):
        super().__init__(f"feature conflict on {attr!r}: {a!r} vs {b!r}")
        self.attr = attr
        self.values = (a, b)


@dataclass(frozen=True)
class Sighting:
    """One observation of an animal at one point in time and space."""

    id: str
    t_min: int            # minutes since an arbitrary epoch
    x_m: float            # planar metres
    y_m: float
    sex: Optional[str] = None         # 'male' / 'female' / None
    age_class: Optional[str] = None   # 'cub' / 'juvenile' / 'adult' / None
    size_class: Optional[str] = None  # 'small' / 'medium' / 'large' / None
    markings: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Sighting.id required")
        if self.sex is not None and self.sex not in VALID_SEX:
            raise ValueError(f"invalid sex {self.sex!r}")
        if self.age_class is not None and self.age_class not in VALID_AGE:
            raise ValueError(f"invalid age_class {self.age_class!r}")
        if self.size_class is not None and self.size_class not in VALID_SIZE:
            raise ValueError(f"invalid size_class {self.size_class!r}")
        if not isinstance(self.markings, frozenset):
            # Accept any iterable on construction; freeze it.
            object.__setattr__(self, "markings", frozenset(self.markings))


@dataclass
class Individual:
    """An estimated unique animal — one cluster of compatible sightings."""

    id: str
    sighting_ids: List[str]
    sex: Optional[str] = None
    age_class: Optional[str] = None
    size_class: Optional[str] = None
    markings: Set[str] = field(default_factory=set)

    @property
    def n_sightings(self) -> int:
        return len(self.sighting_ids)

    def feature_signature(self) -> str:
        """Short human-readable signature of the merged features."""
        parts: List[str] = []
        for label, val in (
            ("sex", self.sex),
            ("age", self.age_class),
            ("size", self.size_class),
        ):
            if val is not None:
                parts.append(f"{label}={val}")
        if self.markings:
            parts.append("markings={" + ",".join(sorted(self.markings)) + "}")
        if not parts:
            return "(no distinguishing features)"
        return ", ".join(parts)


@dataclass
class Resolution:
    """The output of `resolve`: a set of estimated individuals plus the
    mapping from sighting id → individual id and a summary of any forced
    splits."""

    individuals: List[Individual]
    sighting_to_individual: Dict[str, str]
    splits: List[Tuple[str, str]] = field(default_factory=list)
    # `splits` is a list of (sighting_id, reason) — sightings that the
    # resolver could not merge into an existing cluster and so opened a
    # new one. Useful for the diagnostic output.

    @property
    def n_individuals(self) -> int:
        return len(self.individuals)

    def confidence(self, individual_id: str) -> float:
        """Heuristic 0–1 score for how well-constrained this cluster is.

        Cheap proxy: 0.25 per distinguishing feature (sex / age / size /
        any-markings) capped at 1.0. A cluster with no features at all
        scores 0.0; a fully-feature-tagged cluster scores 1.0.
        """
        ind = next((i for i in self.individuals if i.id == individual_id), None)
        if ind is None:
            raise KeyError(individual_id)
        feats = sum(
            1 for v in (ind.sex, ind.age_class, ind.size_class) if v is not None
        )
        if ind.markings:
            feats += 1
        return min(1.0, feats * 0.25)
