"""Unit tests for dawn_walker.timefmt."""

import pytest

from dawn_walker.timefmt import parse_hhmm, format_hhmm, in_window, MINUTES_PER_DAY


class TestParseAndFormat:
    def test_parse_midnight(self):
        assert parse_hhmm("00:00") == 0

    def test_parse_one_minute_to_midnight(self):
        assert parse_hhmm("23:59") == 23 * 60 + 59

    def test_parse_noon(self):
        assert parse_hhmm("12:00") == 12 * 60

    def test_format_round_trip(self):
        for s in ["00:00", "06:30", "12:45", "23:59"]:
            assert format_hhmm(parse_hhmm(s)) == s

    def test_format_handles_wrap(self):
        # minute 1500 = 25:00 = 01:00 next day
        assert format_hhmm(MINUTES_PER_DAY + 60) == "01:00"

    def test_parse_rejects_garbage(self):
        for bad in ["", "12", "12:60", "24:00", "ab:cd", "12-30", "12:0a"]:
            with pytest.raises(ValueError):
                parse_hhmm(bad)

    def test_format_rejects_negative(self):
        with pytest.raises(ValueError):
            format_hhmm(-1)


class TestInWindow:
    def test_simple_window_inside(self):
        # 06:00–10:00, ask 08:00
        assert in_window(8 * 60, 6 * 60, 10 * 60) is True

    def test_simple_window_at_open(self):
        assert in_window(6 * 60, 6 * 60, 10 * 60) is True

    def test_simple_window_at_close(self):
        # half-open: close is excluded
        assert in_window(10 * 60, 6 * 60, 10 * 60) is False

    def test_simple_window_outside(self):
        assert in_window(5 * 60, 6 * 60, 10 * 60) is False
        assert in_window(11 * 60, 6 * 60, 10 * 60) is False

    def test_wrap_around_window_late_night(self):
        # 22:00–04:00, ask 23:30
        assert in_window(23 * 60 + 30, 22 * 60, 4 * 60) is True

    def test_wrap_around_window_early_morning(self):
        # 22:00–04:00, ask 03:30
        assert in_window(3 * 60 + 30, 22 * 60, 4 * 60) is True

    def test_wrap_around_window_outside(self):
        # 22:00–04:00, ask 12:00
        assert in_window(12 * 60, 22 * 60, 4 * 60) is False

    def test_empty_window(self):
        # start == end → never inside
        assert in_window(8 * 60, 6 * 60, 6 * 60) is False
