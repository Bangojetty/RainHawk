"""Unit tests for the compatibility primitives."""

import pytest

from field_spotter.compat import (
    euclidean_m,
    features_compatible,
    features_compatible_with_individual,
    merge_features,
    reachable,
)
from field_spotter.models import FeatureConflict, Individual, Sighting


def s(**kw):
    base = dict(id="s", t_min=0, x_m=0.0, y_m=0.0)
    base.update(kw)
    return Sighting(**base)


class TestFeaturesCompatible:
    def test_both_unknown(self):
        assert features_compatible(s(id="a"), s(id="b"))

    def test_one_known_one_unknown(self):
        assert features_compatible(s(id="a", sex="male"), s(id="b"))

    def test_agree(self):
        assert features_compatible(
            s(id="a", sex="male"), s(id="b", sex="male"),
        )

    def test_disagree_sex(self):
        assert not features_compatible(
            s(id="a", sex="male"), s(id="b", sex="female"),
        )

    def test_disagree_age(self):
        assert not features_compatible(
            s(id="a", age_class="cub"), s(id="b", age_class="adult"),
        )

    def test_disagree_size(self):
        assert not features_compatible(
            s(id="a", size_class="small"), s(id="b", size_class="large"),
        )

    def test_markings_disjoint_nonempty(self):
        assert not features_compatible(
            s(id="a", markings={"x"}), s(id="b", markings={"y"}),
        )

    def test_markings_overlap(self):
        assert features_compatible(
            s(id="a", markings={"x", "y"}), s(id="b", markings={"y", "z"}),
        )

    def test_markings_one_empty(self):
        assert features_compatible(
            s(id="a", markings={"x"}), s(id="b"),
        )


class TestMergeFeatures:
    def _ind(self, **kw):
        defaults = dict(id="I001", sighting_ids=["seed"])
        defaults.update(kw)
        return Individual(**defaults)

    def test_merge_takes_specific(self):
        sex, age, size, mark = merge_features(
            s(id="a", sex="male", markings={"x"}),
            self._ind(),
        )
        assert sex == "male"
        assert age is None
        assert size is None
        assert mark == {"x"}

    def test_merge_keeps_existing_when_new_unknown(self):
        sex, age, size, mark = merge_features(
            s(id="a"),
            self._ind(sex="female"),
        )
        assert sex == "female"

    def test_merge_intersects_markings(self):
        sex, age, size, mark = merge_features(
            s(id="a", markings={"x", "y"}),
            self._ind(markings={"y", "z"}),
        )
        assert mark == {"y"}

    def test_merge_raises_on_disjoint_markings(self):
        with pytest.raises(FeatureConflict):
            merge_features(
                s(id="a", markings={"x"}),
                self._ind(markings={"y"}),
            )

    def test_merge_raises_on_disagreeing_sex(self):
        with pytest.raises(FeatureConflict):
            merge_features(
                s(id="a", sex="male"),
                self._ind(sex="female"),
            )


class TestEuclideanAndReachable:
    def test_euclidean_zero(self):
        assert euclidean_m(s(), s()) == 0.0

    def test_euclidean_known(self):
        assert euclidean_m(s(x_m=3.0, y_m=0.0), s(x_m=0.0, y_m=4.0)) == 5.0

    def test_reachable_simultaneous_colocated(self):
        assert reachable(s(t_min=10, x_m=1, y_m=1), s(t_min=10, x_m=1, y_m=1), 1.0)

    def test_unreachable_simultaneous_apart(self):
        assert not reachable(s(t_min=10, x_m=0, y_m=0), s(t_min=10, x_m=1, y_m=0), 1.0)

    def test_reachable_within_speed(self):
        # 60 m gap, 1 minute = 60 s, max speed 1 m/s → 60m exactly: reachable.
        assert reachable(
            s(t_min=0, x_m=0, y_m=0),
            s(t_min=1, x_m=60, y_m=0),
            max_speed_mps=1.0,
        )

    def test_unreachable_outside_speed(self):
        # Same setup but a smidge further than 60 m.
        assert not reachable(
            s(t_min=0, x_m=0, y_m=0),
            s(t_min=1, x_m=60.001, y_m=0),
            max_speed_mps=1.0,
        )

    def test_reachable_rejects_nonpositive_speed(self):
        with pytest.raises(ValueError):
            reachable(s(), s(t_min=10), max_speed_mps=0.0)


class TestFeaturesCompatibleWithIndividual:
    def test_compat_with_sparse_individual(self):
        ind = Individual(id="I", sighting_ids=["x"])
        assert features_compatible_with_individual(s(sex="male"), ind)

    def test_incompat_via_marking(self):
        ind = Individual(id="I", sighting_ids=["x"], markings={"a"})
        assert not features_compatible_with_individual(
            s(markings={"b"}), ind,
        )
