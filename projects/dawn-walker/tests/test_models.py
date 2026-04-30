"""Unit tests for the dataclass models — input validation."""

import pytest

from dawn_walker.models import POI, TimeWindow, InfeasibleItinerary


class TestTimeWindow:
    def test_simple_window_contains(self):
        w = TimeWindow(open_minute=6 * 60, close_minute=10 * 60)
        assert w.contains(8 * 60)
        assert not w.contains(11 * 60)

    def test_wrap_window_contains(self):
        w = TimeWindow(open_minute=22 * 60, close_minute=4 * 60)
        assert w.contains(23 * 60)
        assert w.contains(3 * 60)
        assert not w.contains(12 * 60)

    def test_str_renders_hhmm(self):
        w = TimeWindow(open_minute=6 * 60 + 30, close_minute=10 * 60)
        assert str(w) == "06:30–10:00"

    def test_rejects_empty_window(self):
        with pytest.raises(ValueError):
            TimeWindow(open_minute=6 * 60, close_minute=6 * 60)

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            TimeWindow(open_minute=-1, close_minute=60)
        with pytest.raises(ValueError):
            TimeWindow(open_minute=60, close_minute=24 * 60)

    def test_rejects_non_int(self):
        with pytest.raises(TypeError):
            TimeWindow(open_minute=6.5, close_minute=10 * 60)  # type: ignore[arg-type]


class TestPOI:
    def _w(self):
        return TimeWindow(open_minute=6 * 60, close_minute=10 * 60)

    def test_valid_poi(self):
        p = POI(
            name="X", category="cat", location=(10.0, 20.0),
            dwell_minutes=15, window=self._w(),
        )
        assert p.name == "X"
        assert p.category == "cat"

    def test_empty_name(self):
        with pytest.raises(ValueError):
            POI(name="", category="c", location=(0.0, 0.0),
                dwell_minutes=10, window=self._w())

    def test_empty_category(self):
        with pytest.raises(ValueError):
            POI(name="n", category="", location=(0.0, 0.0),
                dwell_minutes=10, window=self._w())

    def test_negative_dwell(self):
        with pytest.raises(ValueError):
            POI(name="n", category="c", location=(0.0, 0.0),
                dwell_minutes=-1, window=self._w())

    def test_bad_lat(self):
        with pytest.raises(ValueError):
            POI(name="n", category="c", location=(91.0, 0.0),
                dwell_minutes=10, window=self._w())

    def test_bad_lon(self):
        with pytest.raises(ValueError):
            POI(name="n", category="c", location=(0.0, 181.0),
                dwell_minutes=10, window=self._w())


class TestInfeasibleItinerary:
    def test_carries_diagnostics(self):
        e = InfeasibleItinerary(
            category="x", reason="because", attempts={"a": "closed"},
        )
        assert e.category == "x"
        assert e.reason == "because"
        assert e.attempts == {"a": "closed"}
        assert "x" in str(e)
