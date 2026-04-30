"""Unit tests for the dataclass models."""

import pytest

from field_spotter.models import (
    FeatureConflict,
    Individual,
    Resolution,
    Sighting,
)


def make_sighting(**kw):
    base = dict(id="s", t_min=0, x_m=0.0, y_m=0.0)
    base.update(kw)
    return Sighting(**base)


class TestSighting:
    def test_minimal_valid(self):
        s = make_sighting()
        assert s.id == "s"
        assert s.markings == frozenset()

    def test_freezes_markings(self):
        s = make_sighting(markings={"a", "b"})
        assert isinstance(s.markings, frozenset)
        assert s.markings == frozenset({"a", "b"})

    def test_rejects_empty_id(self):
        with pytest.raises(ValueError):
            make_sighting(id="")

    def test_rejects_invalid_sex(self):
        with pytest.raises(ValueError):
            make_sighting(sex="hermaphrodite")

    def test_rejects_invalid_age(self):
        with pytest.raises(ValueError):
            make_sighting(age_class="elderly")

    def test_rejects_invalid_size(self):
        with pytest.raises(ValueError):
            make_sighting(size_class="huge")

    def test_accepts_known_categorical_values(self):
        for sex in ("male", "female", None):
            for age in ("cub", "juvenile", "adult", None):
                for size in ("small", "medium", "large", None):
                    make_sighting(sex=sex, age_class=age, size_class=size)


class TestIndividual:
    def test_n_sightings(self):
        ind = Individual(id="I001", sighting_ids=["s1", "s2", "s3"])
        assert ind.n_sightings == 3

    def test_signature_no_features(self):
        ind = Individual(id="I001", sighting_ids=["s"])
        assert ind.feature_signature() == "(no distinguishing features)"

    def test_signature_with_features(self):
        ind = Individual(
            id="I001", sighting_ids=["s"],
            sex="male", age_class="adult", size_class="medium",
            markings={"white-tail-tip"},
        )
        sig = ind.feature_signature()
        assert "sex=male" in sig
        assert "age=adult" in sig
        assert "size=medium" in sig
        assert "white-tail-tip" in sig

    def test_signature_orders_markings(self):
        ind = Individual(
            id="I001", sighting_ids=["s"],
            markings={"zebra", "alpha", "moose"},
        )
        sig = ind.feature_signature()
        # markings should appear sorted alphabetically
        idx_a = sig.index("alpha")
        idx_m = sig.index("moose")
        idx_z = sig.index("zebra")
        assert idx_a < idx_m < idx_z


class TestResolution:
    def test_n_individuals(self):
        r = Resolution(individuals=[
            Individual(id="I001", sighting_ids=["s1"]),
            Individual(id="I002", sighting_ids=["s2"]),
        ], sighting_to_individual={"s1": "I001", "s2": "I002"})
        assert r.n_individuals == 2

    def test_confidence_scales_with_features(self):
        none_ind = Individual(id="I001", sighting_ids=["s"])
        full_ind = Individual(
            id="I002", sighting_ids=["s"],
            sex="male", age_class="adult", size_class="medium",
            markings={"x"},
        )
        r = Resolution(
            individuals=[none_ind, full_ind],
            sighting_to_individual={},
        )
        assert r.confidence("I001") == 0.0
        assert r.confidence("I002") == 1.0

    def test_confidence_unknown_id(self):
        r = Resolution(individuals=[], sighting_to_individual={})
        with pytest.raises(KeyError):
            r.confidence("ghost")


class TestFeatureConflict:
    def test_carries_attribute_and_values(self):
        e = FeatureConflict("sex", "male", "female")
        assert e.attr == "sex"
        assert e.values == ("male", "female")
        assert "sex" in str(e)
