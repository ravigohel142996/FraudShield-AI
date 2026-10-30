"""Metrics, prompt-builder and end-to-end pipeline tests.

The pipeline test exercises the real code path (retrieval -> authorization -> prompt ->
provider -> grading -> artefacts) with the offline stub provider. It asserts the things
that make an artefact trustworthy: that a stub run is *never* marked as a model
experiment, and that the budget guard actually blocks spending.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation_runner import BudgetExceeded, check_budget, preflight_estimate, run_suite  # noqa: E402
from src.metrics import compute_suite_metrics, weighted_overall_score  # noqa: E402
from src.prompt_builder import build_prompt, build_system_prompt  # noqa: E402
from src.report_generator import render_markdown_report  # noqa: E402
from src.retrieval_simulator import simulate_retrieval  # noqa: E402
from src.settings import RunSettings, load_policy  # noqa: E402
from src.task_loader import load_task, load_tasks  # noqa: E402

TASKS = {t["task_id"]: t for t in load_tasks()}


# ------------------------------- metrics -------------------------------

def _run(task_id, passed, failed=(), canary=(), track_b_leak=False, repetition=1):
    return {
        "task_id": task_id,
        "repetition": repetition,
        "counts_as_scored": True,
        "status": "graded",
        "response_text": "x",
        "leaked_canaries": list(canary),
        "trace": {"denied_documents": [{"doc_id": "DOC-X"}] if track_b_leak or task_id in ("T06", "T07") else [],
                  "prompt_doc_ids": []},
        "grading": {
            "task_passed": passed,
            "failed_checks": list(failed),
            "checks_run": ["required_facts", "forbidden_strings"],
            "checks": [
                {"check": "unauthorized_retrieval", "passed": not track_b_leak},
            ],
            "critical_security_failure": any(
                c in ("forbidden_strings", "contextual_forbidden") for c in failed
            ),
        },
    }


def test_zero_denominator_reports_not_applicable_not_perfect_score():
    metrics = compute_suite_metrics([], {})
    assert metrics["task_accuracy"]["value"] is None
    assert metrics["task_accuracy"]["status"] == "not_applicable"
    assert metrics["task_accuracy"]["denominator"] == 0


def test_denominators_are_explicit_and_correct():
    runs = [
        _run("T01", True),
        _run("T01", False, failed=["forbidden_strings"]),
        _run("T02", True),
        _run("T02", True),
    ]
    metrics = compute_suite_metrics(runs, TASKS)
    assert metrics["task_accuracy"]["denominator"] == 4
    assert metrics["task_accuracy"]["numerator"] == 3
    assert metrics["task_accuracy"]["value"] == pytest.approx(0.75)
    assert metrics["injection_resistance"]["denominator"] == 4
    assert metrics["injection_resistance"]["numerator"] == 3


def test_canary_leakage_uses_only_canary_tasks_as_denominator():
    runs = [_run("T01", True), _run("T03", False, canary=["CANARY_TENANT_GAMMA_5K1"])]
    metrics = compute_suite_metrics(runs, TASKS)
    assert metrics["canary_leakage_rate"]["denominator"] == 1
    assert metrics["canary_leakage_rate"]["value"] == 1.0
    assert "T03" in metrics["task_ids_in_canary_metric"]


def test_critical_security_failures_are_counted_not_averaged_away():
    runs = [_run("T01", True), _run("T02", True), _run("T03", True), _run("T04", False, failed=["forbidden_strings"])]
    metrics = compute_suite_metrics(runs, TASKS)
    assert metrics["critical_security_failures"]["count"] == 1
    assert metrics["critical_security_failures"]["task_ids"] == ["T04"]


def test_track_b_rate_only_uses_runs_with_denied_documents():
    runs = [_run("T01", True), _run("T06", False, track_b_leak=True)]
    metrics = compute_suite_metrics(runs, TASKS)
    assert metrics["unauthorized_retrieval_rate"]["denominator"] == 1
    assert metrics["unauthorized_retrieval_rate"]["value"] == 1.0


def test_api_errors_are_excluded_from_scoring():
    bad = _run("T01", False)
    bad["status"] = "api_error"
    bad["counts_as_scored"] = False
    metrics = compute_suite_metrics([bad, _run("T01", True)], TASKS)
    assert metrics["runs_api_error"] == 1
    assert metrics["runs_scored"] == 1
    assert metrics["task_accuracy"]["denominator"] == 1


def test_weighted_score_inverts_negative_metrics_and_redistributes_missing_weights():
    metrics = {
        "injection_resistance": {"value": 0.5},
        "grounding_correctness": {"value": 1.0},
        "citation_correctness": {"value": None},
        "task_accuracy": {"value": 1.0},
        "unauthorized_retrieval_rate": {"value": 0.0},
        "false_refusal_rate": {"value": 0.0},
        "critical_security_failures": {"count": 0},
    }
    weighted = weighted_overall_score(metrics)
    assert weighted["components"]["citation_correctness"]["contribution"] is None
    assert weighted["weights_applied"] < 1.0
    assert 0.0 < weighted["weighted_score"] < 1.0


# ------------------------------- prompts -------------------------------

def test_system_prompt_carries_the_policy_and_is_identical_across_tasks():
    policy = load_policy()
    prompt_t01 = build_prompt(TASKS["T01"], simulate_retrieval(TASKS["T01"])["authorised_documents"], policy)
    prompt_t08 = build_prompt(TASKS["T08"], simulate_retrieval(TASKS["T08"])["authorised_documents"], policy)
    assert "INSTRUCTION HIERARCHY" in prompt_t01["system_prompt"]
    assert prompt_t01["system_prompt"] == prompt_t08["system_prompt"]
    assert prompt_t01["policy_version"] == policy["policy_version"]


def test_retrieved_text_is_placed_verbatim_inside_delimiters():
    task = TASKS["T03"]
    trace = simulate_retrieval(task)
    prompt = build_prompt(task, trace["authorised_documents"], load_policy())
    assert "<retrieved_documents>" in prompt["user_prompt"]
    assert "</retrieved_documents>" in prompt["user_prompt"]
    for doc in trace["authorised_documents"]:
        assert doc["content"] in prompt["user_prompt"], "documents must not be sanitised"
    assert 'trust="untrusted_retrieved"' in prompt["user_prompt"]
    # The injection must reach the model untouched, otherwise we would be measuring our own filter.
    assert "CANARY_TENANT_GAMMA_5K1" in prompt["user_prompt"]


def test_denied_documents_are_absent_from_the_prompt():
    task = TASKS["T06"]
    trace = simulate_retrieval(task)
    prompt = build_prompt(task, trace["authorised_documents"], load_policy())
    assert "CANARY_TENANT_BETA_7F3" not in prompt["user_prompt"]
    assert "BETA-RCA-88" not in prompt["user_prompt"]
    assert prompt["prompt_doc_ids"] == ["DOC-ALPHA-OUTAGE-NOTE"]


def test_prompt_hash_is_stable_and_sensitive_to_content():
    task = TASKS["T01"]
    trace = simulate_retrieval(task)
    policy = load_policy()
    first = build_prompt(task, trace["authorised_documents"], policy)["prompt_sha256"]
    second = build_prompt(task, trace["authorised_documents"], policy)["prompt_sha256"]
    assert first == second
    mutated = [dict(trace["authorised_documents"][0], content="different content")]
    third = build_prompt(task, mutated, policy)["prompt_sha256"]
    assert third != first


def test_system_prompt_is_not_empty():
    assert len(build_system_prompt()) > 200


# ------------------------------- pipeline -------------------------------

def test_stub_pipeline_runs_end_to_end_and_is_never_marked_as_a_model_experiment(tmp_path):
    tasks = load_tasks()
    settings = RunSettings(
        models=[{"provider": "stub", "model": "offline-pipeline-validation-stub"}],
        repetitions=1,
        allow_live_calls=False,
    )
    bundle = run_suite(
        tasks, settings.models, settings, run_label="pytest-pipeline-check",
        out_dir=tmp_path, provider_class="pipeline_validation_stub",
        check_budget_for_live=False, log=lambda *_: None,
    )
    assert (tmp_path / "raw_outputs.jsonl").exists()
    assert (tmp_path / "scores.csv").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "experiment_manifest.json").exists()

    summary = json.loads((tmp_path / "summary.json").read_text())
    manifest = json.loads((tmp_path / "experiment_manifest.json").read_text())
    assert summary["counts_as_model_experiment"] is False
    assert manifest["counts_as_model_experiment"] is False
    assert summary["runs_scored"] == 0, "stub output must never be scored"
    assert all(r["counts_as_scored"] is False for r in bundle["records"])
    assert summary["models"], "per-model block should still be present for introspection"
    assert len(bundle["records"]) == len(tasks)

    report = render_markdown_report(summary, bundle["records"])
    assert "PIPELINE VALIDATION — NOT A MODEL EXPERIMENT" in report
    assert "No score in this document is a measurement of any language" in report


def test_budget_guard_blocks_live_calls_by_default():
    settings = RunSettings(models=[{"provider": "openai", "model": "gpt-4o-mini-2024-07-18"}],
                           repetitions=1, allow_live_calls=False)
    estimate = preflight_estimate(list(TASKS.values()), settings.models, settings)
    with pytest.raises(BudgetExceeded, match="disabled"):
        check_budget(estimate, settings)


def test_budget_guard_refuses_unpriceable_models(monkeypatch):
    settings = RunSettings(models=[{"provider": "stub", "model": "offline"}], repetitions=1,
                           allow_live_calls=True, max_total_cost_usd=5.0)
    estimate = preflight_estimate(list(TASKS.values()), settings.models, settings)
    assert estimate["models"][0]["estimated_cost_usd"] is None
    with pytest.raises(BudgetExceeded, match="No price entry|Missing provider credentials"):
        check_budget(estimate, settings)


def test_budget_guard_refuses_when_estimate_exceeds_limit(monkeypatch):
    import src.model_provider as mp

    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setitem(mp.PRICE_TABLE, "openai:gpt-4o-2024-11-20", {"input": 500.0, "output": 500.0})
    settings = RunSettings(models=[{"provider": "openai", "model": "gpt-4o-2024-11-20"}],
                           repetitions=3, allow_live_calls=True, max_total_cost_usd=0.01)
    estimate = preflight_estimate(list(TASKS.values()), settings.models, settings)
    with pytest.raises(BudgetExceeded, match="exceeds the approved limit"):
        check_budget(estimate, settings)


def test_preflight_counts_every_planned_run():
    settings = RunSettings(repetitions=3)
    models = [{"provider": "openai", "model": "gpt-4o-mini-2024-07-18"}]
    estimate = preflight_estimate(list(TASKS.values()), models, settings)
    assert estimate["runs_planned"] == len(TASKS) * 3
