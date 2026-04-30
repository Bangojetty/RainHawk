# Problem log — morning-ritual-planner

Append-only. One entry per bug, roadblock, or surprising "huh, that didn't
work" moment, whether or not it was resolved immediately.

---

## 2026-04-29 — `→` (U+2192) in renderer crashes Windows CLI

**What happened.** All 63 tests passed on first run, but invoking
`python -m dawn_walker plan examples/hanoi_dawn.json` from a Windows shell
crashed with:

```
UnicodeEncodeError: 'charmap' codec can't encode character '→' in
position 137: character maps to <undefined>
```

The renderer used `→` as the connector between the time and the next
stop's name. Python's stdout on Windows defaults to cp1252, which cannot
encode that codepoint. Tests didn't catch it because they run the
renderer through Python strings (no console encoding step).

**What I tried first.** Re-read the traceback: failure is at
`sys.stdout.write(out)`, after `run_plan` returns the rendered string.
That confirmed the issue is encoding at the boundary, not anywhere in the
planner.

**What worked.** Replaced `→` with the ASCII connector `->` in
`dawn_walker/render.py`. Rationale: the renderer's job is a portable
human-readable schedule; an ASCII-only output is robust across consoles
and trivially diff-friendly. Updated the corresponding test that asserted
on the rendered substring.

**Lesson for next time.** Unicode in CLI output is a portability tax that
isn't worth paying for a side-project tool. Default to ASCII. If pretty
glyphs ever matter, gate them behind a `--unicode` flag and detect
`sys.stdout.encoding` first.

---

## 2026-04-29 — Tight flower-market window in initial example was infeasible

**What happened.** The first version of `examples/hanoi_dawn.json` had
the flower market open 22:00–04:30 with a 30-minute dwell, and the walker
leaving the hostel at 03:30. Walking to the market takes ~59 minutes, so
arrival is ~04:29 — inside the window, but a 30-minute dwell would end at
04:59, after the 04:30 close. Hand-traced before running anything; the
planner would have raised `InfeasibleItinerary` on the example. Caught
during a "trace it before you trust it" pass on the example file.

**What worked.** Loosened the flower-market close to 05:00 and moved the
walker's departure to 02:30. The trace then fits cleanly through all six
stops without wasted waiting.

**Lesson.** When the example is also an integration-test fixture,
hand-trace at least one full path before depending on it.

---

## 2026-04-29 — Em-dashes in user data also crash on cp1252

**What happened.** After replacing `→` with `->` in the renderer, running
the CLI again still failed because the example JSON had `—` (U+2014) in
several POI names ("Hostel — Old Quarter", "Ly Thai To Park — Tai Chi",
etc.). Same root cause as before: cp1252-encoded stdout cannot represent
the codepoint.

**What I tried first.** Briefly considered ASCII-only example data, but
the *user's* JSON could legitimately contain any Unicode — POI names in
Vietnamese, Hindi, Chinese, etc. Bowdlerising the example would just push
the bug onto the next user.

**What worked.** Wrapped stdout/stderr writes in a `_safe_write` helper
in `dawn_walker/__main__.py` that re-encodes through the stream's own
encoding with `errors="replace"`. The output gets a `?` (replacement
char) where the console can't render the original codepoint, but the
program completes successfully. Tests still pass — they go through
`run_plan` directly and never touch the cp1252 boundary, but they also
still cover the full happy path of the CLI's `main()`.

**Lesson.** Encoding boundaries are at I/O surfaces, not at the data
layer. Keep data faithful; degrade output gracefully.
