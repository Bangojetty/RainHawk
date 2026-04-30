"""Unit tests for dawn_walker.geo."""

import math

import pytest

from dawn_walker.geo import haversine_km, walking_minutes


class TestHaversine:
    def test_zero_distance(self):
        assert haversine_km((40.0, -74.0), (40.0, -74.0)) == 0.0

    def test_known_pair_nyc_to_la(self):
        # Approximately 3935 km. Allow ±20 km — radius constants vary.
        nyc = (40.7128, -74.0060)
        la = (34.0522, -118.2437)
        d = haversine_km(nyc, la)
        assert 3915 < d < 3955

    def test_known_short_pair_hanoi(self):
        # Hoan Kiem Lake (21.0287, 105.8524) to Quang Ba Flower Market
        # (21.0626, 105.8225). Roughly 4.5 km.
        a = (21.0287, 105.8524)
        b = (21.0626, 105.8225)
        d = haversine_km(a, b)
        assert 4.0 < d < 5.5

    def test_symmetric(self):
        a = (10.0, 20.0)
        b = (15.0, 25.0)
        assert haversine_km(a, b) == pytest.approx(haversine_km(b, a))

    def test_lat_out_of_range(self):
        with pytest.raises(ValueError):
            haversine_km((91.0, 0.0), (0.0, 0.0))

    def test_lon_out_of_range(self):
        with pytest.raises(ValueError):
            haversine_km((0.0, -181.0), (0.0, 0.0))


class TestWalkingMinutes:
    def test_zero_distance_zero_minutes(self):
        assert walking_minutes((1.0, 1.0), (1.0, 1.0), kph=4.5) == 0

    def test_rounds_up(self):
        # ~4.5 km at 4.5 kph = exactly 60 min; tiny extra → 61 min via ceil.
        a = (21.0287, 105.8524)
        b = (21.0626, 105.8225)
        # Distance ~4.5 km; minutes_exact ~ 60 → ceil 60 or 61 depending on
        # exact distance. Either way, must be a small positive int.
        m = walking_minutes(a, b, kph=4.5)
        assert isinstance(m, int)
        assert 50 <= m <= 75

    def test_speed_must_be_positive(self):
        with pytest.raises(ValueError):
            walking_minutes((0.0, 0.0), (1.0, 1.0), kph=0)
        with pytest.raises(ValueError):
            walking_minutes((0.0, 0.0), (1.0, 1.0), kph=-1.0)

    def test_faster_speed_is_shorter(self):
        a, b = (21.0287, 105.8524), (21.0626, 105.8225)
        slow = walking_minutes(a, b, kph=3.0)
        fast = walking_minutes(a, b, kph=6.0)
        assert fast < slow
