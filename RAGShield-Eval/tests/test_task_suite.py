"""Task-suite integrity tests.

These guard the benchmark itself: a task that stops discriminating (because a canary was
removed, a citation target drifted out of the prompt, or the suite drifted away from the
8-task design) fails here rather than silently weakening the published results.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.retrieval_simulator import simulate_retrieval  # noqa: E402
from src.task_loader import load_tasks  # noqa: E402
from src.task_validator import validate_all, validate_task  # noqa: E402

TASKS = load_tasks()
BY_ID = {t["task_id"]: t for t in TASKS}


def test_suite_has_eight_tasks():
    assert len(TASKS) == 8


def test_all_tasks_are_valid():
    errors, _warnings = validate_all(TASKS)
    assert errors == {}, errors


def test_task_ids_and_categories_are_unique():
    ids = [t["task_id"] for t in TASKS]
    categories = [t["category"] for t in TASKS]
    assert len(set(ids)) == len(ids)
    assert len(set(categories)) == len(categories), "each task must test a distinct phenomenon"


def test_task_files_match_their_ids():
    for task in TASKS:
        assert task["_source_file"] == f"task_{task['task_id'][1:]}.json"


def test_every_task_declares_rationale_failure_modes_and_ground_truth():
    for task in TASKS:
        assert len(task["security_rationale"]) > 80
        assert task["expected_failure_patterns"], task["task_id"]
        assert len(task["ground_truth"]) > 60


def test_both_tracks_are_represented():
    tracks = {track for task in TASKS for track in task["track"]}
    assert tracks == {"A", "B"}
    track_b_tasks = [t["task_id"] for t in TASKS if "B" in t["track"]]
    assert track_b_tasks == ["T06", "T07"]


def test_track_b_tasks_actually_deny_something():
    for task_id in ("T06", "T07"):
        trace = simulate_retrieval(BY_ID[task_id])
        assert trace["denied_count"] >= 1, f"{task_id} tests authorization but denies nothing"


def test_each_injection_task_carries_the_injection_into_the_prompt():
    """A task whose injected text never reaches the model measures nothing."""
    expectations = {"T01": "INJECTION_SUCCESS_T01", "T02": "MARKUP_PWNED_T02", "T03": "ADMIN_MODE_ON"}
    for task_id, marker in expectations.items():
        task = BY_ID[task_id]
        trace = simulate_retrieval(task)
        prompt_text = "\n".join(d["content"] for d in trace["authorised_documents"])
        assert marker in prompt_text, f"{task_id}: injection marker {marker!r} missing from context"


def test_suite_contains_positive_controls():
    """At least one task must reward answering, not refusing, so over-refusal is measurable."""
    refusal_control = [t for t in TASKS if t["expected"].get("false_refusal")]
    assert refusal_control, "no false-refusal control in the suite"
    assert any("refusal_required" in t["expected"] and t["expected"]["refusal_required"] for t in TASKS)


def test_suite_spans_multiple_difficulties():
    assert {t["difficulty"] for t in TASKS} >= {"easy", "medium", "hard"}


@pytest.mark.parametrize("task_id", sorted(BY_ID))
def test_task_is_json_round_trippable(task_id):
    task = {k: v for k, v in BY_ID[task_id].items() if not k.startswith("_")}
    assert json.loads(json.dumps(task)) == task


def test_validator_rejects_a_task_with_a_canary_that_is_not_present():
    """Tamper with a task: remove the canary from the document. Validation must fail."""
    task = json.loads(json.dumps({k: v for k, v in BY_ID["T03"].items() if not k.startswith("_")}))
    for doc in task["documents"]:
        doc["content"] = doc["content"].replace("CANARY_TENANT_GAMMA_5K1", "REDACTED")
    errors, _ = validate_task(task)
    assert any("M4" in e for e in errors), errors


def test_validator_rejects_a_citation_target_that_is_not_in_the_prompt():
    task = json.loads(json.dumps({k: v for k, v in BY_ID["T06"].items() if not k.startswith("_")}))
    task["expected"]["required_citations"][0]["doc_ids"] = ["DOC-BETA-POSTMORTEM"]
    errors, _ = validate_task(task)
    assert any("M2" in e for e in errors), errors


def test_validator_rejects_a_track_b_task_without_a_leak_observable():
    task = json.loads(json.dumps({k: v for k, v in BY_ID["T06"].items() if not k.startswith("_")}))
    task["expected"]["forbidden_strings"] = []
    errors, _ = validate_task(task)
    assert any("M5" in e for e in errors), errors
