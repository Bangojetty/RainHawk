"""End-to-end test of the CLI entry point against the bundled example."""

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from dawn_walker.__main__ import main, run_plan


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = PROJECT_ROOT / "examples" / "hanoi_dawn.json"


def test_example_file_exists():
    assert EXAMPLE.exists(), f"missing example fixture: {EXAMPLE}"


def test_run_plan_returns_string_with_expected_stops():
    out = run_plan(EXAMPLE)
    # Each named POI from the fixture should appear in the rendered text.
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for poi in raw["pois"]:
        assert poi["name"] in out, f"missing {poi['name']!r} in:\n{out}"
    # Sanity: starts with a header and includes a Total line.
    assert out.startswith("Dawn walk starting at ")
    assert "Total:" in out


def test_main_zero_exit_on_example():
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = main(["plan", str(EXAMPLE)])
    assert rc == 0, f"stderr: {buf_err.getvalue()}"
    out = buf_out.getvalue()
    assert "Dawn walk starting at" in out


def test_main_usage_on_no_args():
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = main([])
    assert rc == 2
    assert "usage" in buf_err.getvalue()


def test_main_missing_file():
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = main(["plan", str(PROJECT_ROOT / "does-not-exist.json")])
    assert rc == 2
    assert "file not found" in buf_err.getvalue()


def test_main_reports_infeasible(tmp_path: Path):
    # Build a small JSON where no POI of the requested category exists.
    bad = {
        "start": {"label": "Home", "lat": 0.0, "lon": 0.0, "time": "06:00"},
        "walking_kph": 4.5,
        "sequence": ["nonexistent"],
        "pois": [],
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = main(["plan", str(p)])
    assert rc == 1
    err = buf_err.getvalue()
    assert "infeasible" in err
    assert "nonexistent" in err
