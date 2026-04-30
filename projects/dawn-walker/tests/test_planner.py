"""Unit tests for the planner."""

import pytest

from dawn_walker.models import POI, TimeWindow, InfeasibleItinerary
from dawn_walker.planner import plan_itinerary
from dawn_walker.timefmt import parse_hhmm


# A handful of helpers and fixture POIs --------------------------------------

def hhmm(s):
    return parse_hhmm(s)


def make_poi(name, category, location, dwell, open_s, close_s):
    return POI(
        name=name,
        category=category,
        location=location,
        dwell_minutes=dwell,
        window=TimeWindow(open_minute=hhmm(open_s), close_minute=hhmm(close_s)),
    )


# Two points ~1 km apart at the equator-ish for predictable walks.
A = (0.0, 0.0)
B = (0.0, 0.009)  # ~1 km east → 14 min at 4.5 kph
C = (0.0, 0.018)  # ~2 km east → 27 min at 4.5 kph


class TestHappyPath:
    def test_three_stops_fit_with_waiting(self):
        pois = [
            make_poi("market", "produce-market", B, 20, "06:00", "10:00"),
            make_poi("park", "exercise", C, 30, "06:30", "09:00"),
            make_poi("cafe", "breakfast", B, 25, "07:00", "10:00"),
        ]
        it = plan_itinerary(
            start_label="Home",
            start_location=A,
            start_minute=hhmm("05:30"),
            category_sequence=["produce-market", "exercise", "breakfast"],
            pois=pois,
            walking_kph=4.5,
        )
        assert len(it.stops) == 3
        assert [s.poi.category for s in it.stops] == [
            "produce-market", "exercise", "breakfast",
        ]
        # Each visit fits inside its window.
        for s in it.stops:
            assert s.poi.window.contains(s.arrive_minute)
            # depart_minute may equal close exactly (half-open boundary).
            assert s.depart_minute <= s.poi.window.close_minute or (
                s.poi.window.close_minute < s.poi.window.open_minute
            )
        # Stops are time-ordered.
        for prev, nxt in zip(it.stops, it.stops[1:]):
            assert prev.depart_minute <= nxt.arrive_minute

    def test_walker_waits_for_window_open(self):
        # Walker arrives long before the window opens.
        pois = [make_poi("park", "exercise", B, 15, "07:00", "09:00")]
        it = plan_itinerary(
            "Home", A, hhmm("05:00"), ["exercise"], pois,
        )
        # Should have waited until 07:00 to start the visit.
        assert it.stops[0].arrive_minute == hhmm("07:00")

    def test_zero_dwell_is_a_visit(self):
        pois = [make_poi("vista", "photo", B, 0, "06:00", "06:30")]
        it = plan_itinerary("Home", A, hhmm("05:30"), ["photo"], pois)
        assert it.stops[0].arrive_minute == hhmm("06:00")
        assert it.stops[0].depart_minute == hhmm("06:00")


class TestWrapAroundWindow:
    def test_night_only_market(self):
        # Flower market open 22:00–04:00 (wraps midnight).
        pois = [make_poi("flower", "flower-market", B, 20, "22:00", "04:00")]
        it = plan_itinerary("Home", A, hhmm("03:00"), ["flower-market"], pois)
        # Walker arrives ~03:14 and that's inside the wrap-window; dwell 20
        # ends 03:34, also in window.
        s = it.stops[0]
        assert hhmm("03:00") <= s.arrive_minute < hhmm("04:00")
        assert s.depart_minute <= hhmm("04:00")

    def test_wrap_window_dwell_overruns_close(self):
        # Window 22:00–04:00, walker arrives 03:50, dwell 30 → 04:20 > close.
        # Planner should wait until next day's 22:00.
        pois = [make_poi("flower", "flower-market", A, 30, "22:00", "04:00")]
        it = plan_itinerary("Home", A, hhmm("03:50"), ["flower-market"], pois)
        # Next opening at 22:00 today (1320 minutes) — that's > start_minute 230.
        assert it.stops[0].arrive_minute == 22 * 60


class TestInfeasibility:
    def test_no_candidates_for_category(self):
        pois = [make_poi("p", "exercise", B, 10, "06:00", "08:00")]
        with pytest.raises(InfeasibleItinerary) as ei:
            plan_itinerary("Home", A, hhmm("05:30"), ["breakfast"], pois)
        assert ei.value.category == "breakfast"
        assert "no POI of category" in ei.value.reason

    def test_window_closes_before_walker_arrives(self):
        # Window 05:00-05:30. Walker leaves 06:00. Arrival 06:14. Next window
        # is tomorrow 05:00 — within 24h horizon, but actually 23h away. The
        # planner *will* schedule it for tomorrow. We then assert the raised
        # case by giving an even tighter window.
        # To make truly infeasible: dwell longer than window length.
        pois = [make_poi("p", "exercise", B, 60, "07:00", "07:30")]  # 30-min window
        with pytest.raises(InfeasibleItinerary) as ei:
            plan_itinerary("Home", A, hhmm("05:00"), ["exercise"], pois)
        assert ei.value.category == "exercise"
        # Diagnostics carry the failure reason for the candidate.
        assert "p" in ei.value.attempts
        assert "cannot fit" in ei.value.attempts["p"]


class TestCandidateSelection:
    def test_picks_soonest_departure(self):
        # Two breakfast spots: same dwell, B is closer (14 min walk), C is
        # farther (27 min). Both windows wide open. Planner should pick B.
        pois = [
            make_poi("far", "breakfast", C, 20, "06:00", "10:00"),
            make_poi("near", "breakfast", B, 20, "06:00", "10:00"),
        ]
        it = plan_itinerary("Home", A, hhmm("06:00"), ["breakfast"], pois)
        assert it.stops[0].poi.name == "near"

    def test_picks_only_feasible_when_others_are_closed(self):
        # Two photo spots; only one window covers walker's arrival.
        pois = [
            make_poi("dawn-only", "photo", B, 10, "05:00", "05:30"),
            make_poi("anytime", "photo", B, 10, "05:00", "12:00"),
        ]
        it = plan_itinerary("Home", A, hhmm("06:00"), ["photo"], pois)
        # Walker leaves 06:00 → arrives ~06:14, only "anytime" fits.
        assert it.stops[0].poi.name == "anytime"

    def test_does_not_reuse_same_poi(self):
        # Two stops, same category. Each must use a different POI.
        pois = [
            make_poi("a", "photo", B, 10, "05:00", "12:00"),
            make_poi("b", "photo", C, 10, "05:00", "12:00"),
        ]
        it = plan_itinerary(
            "Home", A, hhmm("06:00"), ["photo", "photo"], pois,
        )
        names = {s.poi.name for s in it.stops}
        assert names == {"a", "b"}


class TestInputValidation:
    def test_empty_sequence_rejected(self):
        with pytest.raises(ValueError):
            plan_itinerary("Home", A, hhmm("05:00"), [], [])

    def test_negative_walking_speed_rejected(self):
        with pytest.raises(ValueError):
            plan_itinerary(
                "Home", A, hhmm("05:00"), ["x"], [], walking_kph=-1.0,
            )

    def test_start_minute_out_of_range(self):
        with pytest.raises(ValueError):
            plan_itinerary("Home", A, 24 * 60, ["x"], [])


class TestLegMetadata:
    def test_first_leg_starts_at_start_minute(self):
        pois = [make_poi("p", "x", B, 10, "00:00", "23:59")]
        it = plan_itinerary("Home", A, hhmm("06:00"), ["x"], pois)
        assert it.legs[0].depart_minute == hhmm("06:00")
        assert it.legs[0].from_label == "Home"
        assert it.legs[0].to_label == "p"

    def test_legs_count_equals_stops_count(self):
        pois = [
            make_poi("p1", "x", B, 5, "00:00", "23:59"),
            make_poi("p2", "y", C, 5, "00:00", "23:59"),
        ]
        it = plan_itinerary("Home", A, hhmm("06:00"), ["x", "y"], pois)
        assert len(it.legs) == len(it.stops) == 2
