"""field_spotter — small toolkit for analyzing wildlife observation logs.

Public surface kept small intentionally. Import what you need from
submodules. This module re-exports the most common types and functions.
"""

from field_spotter.models import (
    Sighting,
    Individual,
    Resolution,
    FeatureConflict,
)
from field_spotter.compat import (
    features_compatible,
    merge_features,
    reachable,
)
from field_spotter.resolver import resolve
from field_spotter.explain import explain

__all__ = [
    "Sighting",
    "Individual",
    "Resolution",
    "FeatureConflict",
    "features_compatible",
    "merge_features",
    "reachable",
    "resolve",
    "explain",
]
