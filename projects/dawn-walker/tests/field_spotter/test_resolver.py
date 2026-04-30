"""Tests for the resolver."""

import pytest

from field_spotter.models import Sighting
from field_spotter.resolver import resolve


def make(id_, t_min, x, y, **kw):
    return Sighting(id=id_, t_min=t_min, x_m=x, y_m=y, **kw)


class TestEdgeCases:
    def test_empty_input(self):
        r = resolve([], max_speed_mps=10.0)
        assert r.n_individuals == 0
        assert r.sighting_to_individual == {}

    def test_single_sighting(self):
        r = resolve([make("s1", 0, 0.0, 0.0)], max_speed_mps=10.0)
        assert r.n_individuals == 1
        assert r.sighting_to_individual == {"s1": "I001"}

    def test_rejects_nonpositive_speed(self):
        with pytest.raises(ValueError):
            resolve([], max_speed_mps=0.0)


class TestSimpleMerges:
    def test_two_close_sightings_merge(self):
        # 1 metre apart, 1 minute apart, max 10 m/s — easily reachable.
        ss = [
            make("s1", 0, 0.0, 0.0),
            make("s2", 1, 1.0, 0.0),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        assert r.n_individuals == 1

    def test_simultaneous_far_apart_split(self):
        ss = [
            make("s1", 5, 0.0, 0.0),
            make("s2", 5, 100.0, 0.0),
        ]
        # Same minute, different places → cannot be the same animal.
        r = resolve(ss, max_speed_mps=10.0)
        assert r.n_individuals == 2

    def test_too_fast_for_speed_limit(self):
        # 1000 m apart, 1 minute apart, max 1 m/s → unreachable.
        ss = [
            make("s1", 0, 0.0, 0.0),
            make("s2", 1, 1000.0, 0.0),
        ]
        r = resolve(ss, max_speed_mps=1.0)
        assert r.n_individuals == 2


class TestFeatureSplits:
    def test_sex_conflict_forces_split(self):
        ss = [
            make("s1", 0, 0.0, 0.0, sex="male"),
            make("s2", 1, 1.0, 0.0, sex="female"),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        assert r.n_individuals == 2

    def test_age_conflict_forces_split(self):
        ss = [
            make("s1", 0, 0.0, 0.0, age_class="adult"),
            make("s2", 1, 1.0, 0.0, age_class="cub"),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        assert r.n_individuals == 2

    def test_disjoint_markings_force_split(self):
        ss = [
            make("s1", 0, 0.0, 0.0, markings=frozenset({"white-paw"})),
            make("s2", 1, 1.0, 0.0, markings=frozenset({"ear-tuft"})),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        assert r.n_individuals == 2

    def test_overlapping_markings_merge(self):
        ss = [
            make("s1", 0, 0.0, 0.0, markings=frozenset({"a", "b"})),
            make("s2", 1, 1.0, 0.0, markings=frozenset({"b", "c"})),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        assert r.n_individuals == 1
        # Merged markings should be the intersection {b}.
        assert r.individuals[0].markings == {"b"}


class TestUnknownFeatures:
    def test_one_unknown_one_known_can_merge(self):
        ss = [
            make("s1", 0, 0.0, 0.0, sex="male"),
            make("s2", 1, 1.0, 0.0),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        assert r.n_individuals == 1
        # Cluster inherits the known sex.
        assert r.individuals[0].sex == "male"

    def test_unknown_picks_closest_cluster_when_multiple(self):
        # Three sightings: two distinct males with different markings, then
        # an unknown-marking sighting close to one of them. The unknown
        # has no features, so it's compatible with both, but the closer
        # one should win.
        ss = [
            make("s1", 0, 0.0, 0.0, sex="male", markings=frozenset({"a"})),
            make("s2", 0, 100.0, 0.0, sex="male", markings=frozenset({"b"})),
            make("s3", 1, 1.0, 0.0, sex="male"),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        # 2 individuals; s3 should join s1's cluster (closer + earlier-id tiebreak).
        assert r.n_individuals == 2
        assert r.sighting_to_individual["s3"] == r.sighting_to_individual["s1"]


class TestDeterminism:
    def test_same_input_same_output(self):
        ss = [
            make("s1", 0, 0.0, 0.0, sex="male"),
            make("s2", 1, 1.0, 0.0, sex="male"),
            make("s3", 0, 50.0, 50.0, sex="female"),
            make("s4", 5, 51.0, 51.0, sex="female"),
        ]
        r1 = resolve(ss, max_speed_mps=10.0)
        r2 = resolve(list(reversed(ss)), max_speed_mps=10.0)
        # Same partition (set-of-sets representation), same individual count.
        def canonical(r):
            return sorted(
                tuple(sorted(ind.sighting_ids)) for ind in r.individuals
            )
        assert canonical(r1) == canonical(r2)

    def test_individual_ids_are_sequential(self):
        ss = [
            make("s1", 0, 0.0, 0.0, sex="male"),
            make("s2", 1, 100.0, 100.0, sex="female"),
            make("s3", 2, 200.0, 200.0, age_class="cub"),
        ]
        r = resolve(ss, max_speed_mps=0.5)  # too slow to ever merge
        ids = [ind.id for ind in r.individuals]
        assert ids == ["I001", "I002", "I003"]


class TestGardenScenario:
    """Mini integration test mirroring the bundled example in shape."""

    def test_two_adults_two_cubs(self):
        ss = [
            # Dog fox runs across the lawn early on.
            make("a1", 0, 0.0, 0.0, sex="male", age_class="adult",
                 markings=frozenset({"white-tail-tip"})),
            make("a2", 3, 12.0, 4.0, sex="male", age_class="adult",
                 markings=frozenset({"white-tail-tip"})),
            # Vixen seen at the back fence.
            make("a3", 5, 30.0, 18.0, sex="female", age_class="adult",
                 markings=frozenset({"scar-left-ear"})),
            # Two cubs, distinguishable.
            make("a4", 17, 5.0, 2.0, age_class="cub",
                 markings=frozenset({"white-paw"})),
            make("a5", 19, 6.5, 2.5, age_class="cub",
                 markings=frozenset({"ear-tuft"})),
            make("a6", 25, 22.0, 11.0, age_class="cub",
                 markings=frozenset({"white-paw"})),
        ]
        r = resolve(ss, max_speed_mps=13.0)
        # Expect 4 individuals: dog, vixen, cub-A (white-paw), cub-B (ear-tuft).
        assert r.n_individuals == 4
        # Cub clusters track their markings.
        cub_clusters = [i for i in r.individuals if i.age_class == "cub"]
        marks = sorted(tuple(sorted(c.markings)) for c in cub_clusters)
        assert marks == [("ear-tuft",), ("white-paw",)]


class TestSplitsRecord:
    def test_first_sighting_recorded_as_split(self):
        ss = [make("s1", 0, 0.0, 0.0)]
        r = resolve(ss, max_speed_mps=10.0)
        assert r.splits == [("s1", "first sighting")]

    def test_subsequent_split_carries_reason(self):
        ss = [
            make("s1", 0, 0.0, 0.0, sex="male"),
            make("s2", 1, 1.0, 0.0, sex="female"),
        ]
        r = resolve(ss, max_speed_mps=10.0)
        # s2 opened a new cluster because of feature conflict.
        reasons = dict(r.splits)
        assert "s1" in reasons and "s2" in reasons
        assert reasons["s2"] == "no compatible cluster"
