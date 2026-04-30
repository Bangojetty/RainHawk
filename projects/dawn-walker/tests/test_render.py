"""Unit tests for dawn_walker.render."""

from dawn_walker.models import POI, TimeWindow
from dawn_walker.planner import plan_itinerary
from dawn_walker.render import render_itinerary
from dawn_walker.timefmt import parse_hhmm


def hhmm(s):
    return parse_hhmm(s)


def make_poi(name, category, location, dwell, open_s, close_s):
    return POI(
        name=name, category=category, location=location, dwell_minutes=dwell,
        window=TimeWindow(open_minute=hhmm(open_s), close_minute=hhmm(close_s)),
    )


def test_render_contains_header_and_total():
    pois = [
        make_poi("Park", "exercise", (0.0, 0.009), 30, "06:00", "09:00"),
        make_poi("Cafe", "breakfast", (0.0, 0.018), 25, "07:00", "10:00"),
    ]
    it = plan_itinerary(
        "Hostel", (0.0, 0.0), hhmm("05:30"),
        ["exercise", "breakfast"], pois,
    )
    out = render_itinerary(it)
    assert "Dawn walk starting at Hostel (05:30)" in out
    assert "Park (exercise)" in out
    assert "Cafe (breakfast)" in out
    assert "arrive" in out
    assert "depart" in out
    assert "Total:" in out
    assert "stops" in out


def test_render_lines_in_chronological_order():
    pois = [
        make_poi("A", "x", (0.0, 0.009), 10, "06:00", "10:00"),
        make_poi("B", "y", (0.0, 0.018), 10, "06:00", "10:00"),
    ]
    it = plan_itinerary("Start", (0.0, 0.0), hhmm("06:00"), ["x", "y"], pois)
    out = render_itinerary(it)
    # Find the indices of "A (x)" and "B (y)" — A must come first.
    a_idx = out.index("A (x)")
    b_idx = out.index("B (y)")
    assert a_idx < b_idx


def test_empty_itinerary_renders_message():
    # We can't construct an Itinerary with zero stops via the planner (it
    # rejects empty sequences). Build one directly.
    from dawn_walker.models import Itinerary
    it = Itinerary(
        start_label="Nowhere",
        start_location=(0.0, 0.0),
        start_minute=0,
        stops=[],
        legs=[],
    )
    out = render_itinerary(it)
    assert "empty itinerary" in out


def test_render_includes_walking_minutes():
    pois = [make_poi("Far", "x", (0.0, 0.018), 5, "06:00", "10:00")]
    it = plan_itinerary("Start", (0.0, 0.0), hhmm("06:00"), ["x"], pois)
    out = render_itinerary(it)
    # "walk  N min" with the leg's actual minute count.
    leg_min = it.legs[0].minutes
    assert f"walk  {leg_min:>3d} min" in out
