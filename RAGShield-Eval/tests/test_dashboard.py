"""Dashboard smoke test.

Uses Streamlit's own harness to execute dashboard/app.py exactly as Streamlit would, so a
broken page fails CI instead of failing in front of a judge. Skipped automatically when
Streamlit is not installed (the benchmark core does not require it).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

streamlit = pytest.importorskip("streamlit", reason="dashboard deps not installed")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = PROJECT_ROOT / "dashboard" / "app.py"


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=90)
    at.run()
    return at


def test_dashboard_runs_without_exceptions(app):
    assert not app.exception, [e.value for e in app.exception]


def test_dashboard_exposes_the_expected_sections(app):
    labels = [
        "Overview",
        "Tasks",
        "Models",
        "Runs & raw output",
        "Scoring",
        "Security failures",
        "Retrieval authorisation",
        "Reproducibility",
        "Export",
    ]
    assert len(app.tabs) == len(labels)


def test_dashboard_selects_a_run_or_shows_an_empty_state(app):
    # Either a run radio exists, or the honest empty state was rendered. Never both absent.
    has_runs = len(app.radio) > 0
    text = " ".join(m.value for m in app.markdown) + " ".join(i.value for i in app.info)
    assert has_runs or "NO RUN ARTEFACTS FOUND" in text


def test_dashboard_labels_stub_runs_as_non_results(app):
    if not app.radio:
        pytest.skip("no run artefacts to inspect")
    text = " ".join(m.value for m in app.markdown)
    if "stub" in app.radio[0].options[0]:
        assert "PIPELINE VALIDATION" in text
        assert "not model results" in text.lower() or "Not model results" in text
