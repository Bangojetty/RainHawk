# Feature idea — morning-ritual-planner

## The idea (plain English)

Given a city, a starting point, a dawn time, and a list of candidate "ritual" stops — each tagged with a category (e.g. *flower-market*, *ceremony*, *produce-market*, *exercise*, *photo*, *breakfast*), a geographic location, a dwell duration, and an open-time window — produce a single chronological dawn-to-mid-morning itinerary that visits one stop per requested category in a sensible order, respecting each stop's open window and the walking time between consecutive stops. The walker should be able to print the result as a human-readable schedule with arrival times, departure times, and walking legs.

## Rationale — tying back to the captured sentences

The Hanoi article describes a sequenced morning that hops between distinct kinds of place: a flower market that is *open at night only*, a *ceremony that happens every morning*, a *traditional open-door market*, *Tai Chi at Ly Thai To Statue park*, photographs of the lake, and finally *Pho and iced coffee in the Old Quarter*. Three things stood out:

1. **Order matters and is constrained by time windows.** The flower market is night-only, so it must come before sunrise. Breakfast comes after the exercise hour. A naive "visit them in any order" planner would fail.
2. **Each stop has its own dwell time and category.** A walker doesn't want two flower markets — they want *one* of each ritual type, sequenced.
3. **There is walking between stops, and it costs minutes.** "Head to the Old Quarter" implies a non-trivial walk that has to fit in the schedule.

The smallest interesting kernel of those observations is a planner that takes (POIs with windows + walking speed + a desired category sequence + a start time) and emits a feasible itinerary, rejecting infeasible inputs with a clear reason. That is what this feature builds.
