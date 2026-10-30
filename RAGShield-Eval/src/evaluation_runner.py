"""Experiment orchestration: retrieval -> authorization -> prompt -> model -> grade.

Responsibilities are deliberately narrow. This module owns sequencing and record
keeping; it does not implement grading, authorization, prompting or provider clients.

Failure taxonomy (kept separate on purpose, see FAILURE_ANALYSIS.md):
  api_error       the provider call failed -> excluded from scoring, never counted as a
                  model failure
  empty_response  the call succeeded but returned no text -> recorded as a model-side
                  empty response, excluded from scoring but reported
  graded          a response exists and was graded
Authorization failures are not in this list because they are a property of the
retrieval layer and are recorded in the trace, not inferred from the model.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .graders import grade_response, leaked_canaries
from .metrics import compute_suite_metrics, per_task_summary, weighted_overall_score
from .model_provider import CompletionRequest, get_provider
from .prompt_builder import build_prompt
from .reproducibility import utc_now
from .retrieval_simulator import simulate_retrieval
from .settings import RunSettings, dump_json, load_policy


class BudgetExceeded(RuntimeError):
    pass


def _estimate_tokens(text: str) -> int:
    # Conservative 4-characters-per-token heuristic; only used for pre-flight budget.
    return max(1, len(text) // 4)


def preflight_estimate(
    tasks: List[Dict[str, Any]], models: List[Dict[str, str]], settings: RunSettings
) -> Dict[str, Any]:
    """Worst-case cost estimate BEFORE any call is made."""
    policy = load_policy()
    total = 0.0
    per_model: List[Dict[str, Any]] = []
    task_prompts = []
    for task in tasks:
        trace = simulate_retrieval(task)
        prompt = build_prompt(task, trace["authorised_documents"], policy)
        task_prompts.append(prompt)

    for entry in models:
        provider = get_provider(entry["provider"], entry["model"],
                                max_retries=settings.max_retries,
                                backoff=settings.retry_backoff_seconds)
        input_tokens = sum(
            _estimate_tokens(p["system_prompt"]) + _estimate_tokens(p["user_prompt"])
            for p in task_prompts
        ) * settings.repetitions
        output_tokens = settings.max_output_tokens * len(tasks) * settings.repetitions
        cost = provider.estimated_cost_usd(input_tokens, output_tokens)
        per_model.append(
            {
                "provider": entry["provider"],
                "model": entry["model"],
                "credential": provider.availability_note(),
                "available": provider.available(),
                "estimated_input_tokens": input_tokens,
                "estimated_output_tokens": output_tokens,
                "estimated_cost_usd": cost,
            }
        )
        if cost is not None:
            total += cost
    return {
        "models": per_model,
        "estimated_total_cost_usd": round(total, 4),
        "label": "ESTIMATE - not a billed amount",
        "runs_planned": len(tasks) * len(models) * settings.repetitions,
    }


def check_budget(estimate: Dict[str, Any], settings: RunSettings) -> None:
    if not settings.allow_live_calls:
        raise BudgetExceeded(
            "Live API calls are disabled. Set budget.allow_live_calls: true in "
            "config/benchmark.yaml only after approving a spending limit."
        )
    unavailable = [m for m in estimate["models"] if not m["available"]]
    if unavailable:
        missing = ", ".join(f"{m['provider']}({m['credential']})" for m in unavailable)
        raise BudgetExceeded(f"Missing provider credentials: {missing}")
    total = estimate["estimated_total_cost_usd"]
    if total > settings.max_total_cost_usd:
        raise BudgetExceeded(
            f"Estimated worst-case cost ${total:.2f} exceeds the approved limit "
            f"${settings.max_total_cost_usd:.2f}. Reduce repetitions or models and "
            "re-run; the limit is never raised silently."
        )
    unknown_price = [m["model"] for m in estimate["models"] if m["estimated_cost_usd"] is None]
    if unknown_price:
        raise BudgetExceeded(
            f"No price entry for {unknown_price} in model_provider.PRICE_TABLE, so the "
            "budget guard cannot bound the spend. Add a price entry deliberately."
        )


def run_task_against_model(
    task: Dict[str, Any],
    provider_entry: Dict[str, str],
    settings: RunSettings,
    repetition: int,
    run_label: str,
    provider_class: str = "llm_api",
) -> Dict[str, Any]:
    policy = load_policy()
    trace = simulate_retrieval(task)
    prompt = build_prompt(task, trace["authorised_documents"], policy)

    provider = get_provider(
        provider_entry["provider"],
        provider_entry["model"],
        max_retries=settings.max_retries,
        backoff=settings.retry_backoff_seconds,
    )
    request = CompletionRequest(
        model=provider_entry["model"],
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        temperature=settings.temperature,
        max_output_tokens=settings.max_output_tokens,
        timeout_seconds=settings.timeout_seconds,
    )
    started = utc_now()
    result = provider.complete(request)

    record: Dict[str, Any] = {
        "run_label": run_label,
        "started_utc": started,
        "task_id": task["task_id"],
        "task_category": task.get("category"),
        "task_difficulty": task.get("difficulty"),
        "track": task.get("track"),
        "provider": provider_entry["provider"],
        "model_id": provider_entry["model"],
        "provider_class": provider_class,
        "repetition": repetition,
        "temperature": settings.temperature,
        "max_output_tokens": settings.max_output_tokens,
        "policy_version": prompt["policy_version"],
        "prompt_sha256": prompt["prompt_sha256"],
        "system_prompt_sha256": __import__("hashlib").sha256(
            prompt["system_prompt"].encode("utf-8")
        ).hexdigest(),
        "user_prompt_sha256": __import__("hashlib").sha256(
            prompt["user_prompt"].encode("utf-8")
        ).hexdigest(),
        "prompt_doc_ids": prompt["prompt_doc_ids"],
        "retrieval_trace": {
            k: trace[k]
            for k in (
                "retrieval_query", "top_k", "candidates", "ranked", "retrieved_doc_ids",
                "prompt_doc_ids", "excluded_doc_ids", "exclusions", "authorization_decisions",
                "authorised_count", "denied_count",
            )
        },
        "request_metadata": {
            "timeout_seconds": settings.timeout_seconds,
            "max_retries": settings.max_retries,
            "system_prompt_chars": prompt["system_prompt_chars"],
            "user_prompt_chars": prompt["user_prompt_chars"],
        },
        "usage": {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "latency_ms": result.latency_ms,
            "attempts": result.attempts,
        },
        "estimated_cost_usd": provider.estimated_cost_usd(
            result.input_tokens or 0, result.output_tokens or 0
        ),
        "cost_label": "estimate",
        "error": None,
    }

    if not result.ok:
        record.update(
            {
                "status": "api_error",
                "counts_as_scored": False,
                "response_text": "",
                "error": {
                    "type": result.error_type,
                    "message": result.error_message,
                    "http_status": result.http_status,
                },
                "grading": None,
                "leaked_canaries": [],
            }
        )
        return record

    response_text = result.text or ""
    if not response_text.strip():
        record.update(
            {
                "status": "empty_response",
                "counts_as_scored": False,
                "response_text": "",
                "grading": None,
                "leaked_canaries": [],
            }
        )
        return record

    grading = grade_response(task, response_text, trace, prompt["prompt_doc_ids"])
    record.update(
        {
            "status": "graded",
            "counts_as_scored": provider_class != "pipeline_validation_stub",
            "response_text": response_text,
            "grading": grading,
            "leaked_canaries": leaked_canaries(task, response_text),
            "raw_response": result.raw_response,
        }
    )
    return record


def run_suite(
    tasks: List[Dict[str, Any]],
    models: List[Dict[str, str]],
    settings: RunSettings,
    run_label: str,
    out_dir: Path,
    provider_class: str = "llm_api",
    check_budget_for_live: bool = True,
    log=print,
) -> Dict[str, Any]:
    """Execute every (model, task, repetition) and write raw/summary artefacts."""
    from .reproducibility import build_manifest

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    estimate = preflight_estimate(tasks, models, settings)
    if check_budget_for_live:
        check_budget(estimate, settings)
    log(f"preflight: {estimate['runs_planned']} planned runs, "
        f"estimated worst-case cost ${estimate['estimated_total_cost_usd']:.4f} (estimate)")

    records: List[Dict[str, Any]] = []
    for entry in models:
        for task in tasks:
            for repetition in range(1, settings.repetitions + 1):
                log(f"  run {entry['provider']}:{entry['model']} {task['task_id']} "
                    f"rep {repetition}/{settings.repetitions}")
                records.append(
                    run_task_against_model(
                        task, entry, settings, repetition, run_label, provider_class
                    )
                )

    raw_path = out_dir / "raw_outputs.jsonl"
    with raw_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=False) + "\n")

    tasks_by_id = {t["task_id"]: t for t in tasks}
    models_out: Dict[str, Any] = {}
    for entry in models:
        key = f"{entry['provider']}:{entry['model']}"
        subset = [r for r in records if r["provider"] == entry["provider"] and r["model_id"] == entry["model"]]
        metrics = compute_suite_metrics(subset, tasks_by_id)
        models_out[key] = {
            "provider": entry["provider"],
            "model_id": entry["model"],
            "provider_class": provider_class,
            "metrics": metrics,
            "weighted": weighted_overall_score(metrics),
            "per_task": per_task_summary(subset),
        }

    policy = load_policy()
    counts_as_model_experiment = provider_class == "llm_api"
    manifest = build_manifest(
        run_label=run_label,
        settings_snapshot={
            "repetitions": settings.repetitions,
            "temperature": settings.temperature,
            "max_output_tokens": settings.max_output_tokens,
            "timeout_seconds": settings.timeout_seconds,
            "max_retries": settings.max_retries,
            "budget_limit_usd": settings.max_total_cost_usd,
        },
        policy=policy,
        tasks=tasks,
        models=models,
        runs_total=len(records),
        runs_scored=sum(1 for r in records if r["counts_as_scored"]),
        runs_failed=sum(1 for r in records if r["status"] != "graded"),
        estimated_cost_usd=sum(
            (r.get("estimated_cost_usd") or 0.0) for r in records
        ) if counts_as_model_experiment else 0.0,
        counts_as_model_experiment=counts_as_model_experiment,
        extra={
            "provider_class": provider_class,
            "preflight_estimate": estimate,
            "artefact_note": (
                "Pipeline-validation artefacts. These are NOT model experiment results "
                "and must never be reported as such."
                if not counts_as_model_experiment
                else "Real model experiment. Every record is a genuine provider response."
            ),
        },
    )

    summary = {
        "run_label": run_label,
        "created_utc": utc_now(),
        "counts_as_model_experiment": counts_as_model_experiment,
        "provider_class": provider_class,
        "models": models_out,
        "runs_total": len(records),
        "runs_scored": sum(1 for r in records if r["counts_as_scored"]),
        "runs_api_error": sum(1 for r in records if r["status"] == "api_error"),
        "estimated_total_cost_usd": manifest["cost"]["estimated_total_usd"],
        "cost_label": "estimate",
        "preflight_estimate": estimate,
    }

    dump_json(out_dir / "summary.json", summary)
    dump_json(out_dir / "experiment_manifest.json", manifest)
    _write_scores_csv(out_dir / "scores.csv", records)

    # summaries keyed by model for the dashboard
    dump_json(out_dir / "per_task.json", {m: v["per_task"] for m, v in models_out.items()})
    return {"records": records, "summary": summary, "manifest": manifest}


def _write_scores_csv(path: Path, records: List[Dict[str, Any]]) -> None:
    import csv

    fieldnames = [
        "run_label", "task_id", "task_category", "task_difficulty", "provider", "model_id",
        "provider_class", "repetition", "status", "counts_as_scored", "task_passed",
        "critical_security_failure", "failed_checks", "leaked_canaries",
        "prompt_doc_ids", "excluded_doc_ids", "input_tokens", "output_tokens",
        "latency_ms", "estimated_cost_usd", "prompt_sha256", "started_utc",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            grading = record.get("grading") or {}
            writer.writerow(
                {
                    "run_label": record.get("run_label"),
                    "task_id": record.get("task_id"),
                    "task_category": record.get("task_category"),
                    "task_difficulty": record.get("task_difficulty"),
                    "provider": record.get("provider"),
                    "model_id": record.get("model_id"),
                    "provider_class": record.get("provider_class"),
                    "repetition": record.get("repetition"),
                    "status": record.get("status"),
                    "counts_as_scored": record.get("counts_as_scored"),
                    "task_passed": grading.get("task_passed"),
                    "critical_security_failure": grading.get("critical_security_failure"),
                    "failed_checks": "|".join(grading.get("failed_checks") or []),
                    "leaked_canaries": "|".join(record.get("leaked_canaries") or []),
                    "prompt_doc_ids": "|".join(record.get("prompt_doc_ids") or []),
                    "excluded_doc_ids": "|".join(
                        (record.get("retrieval_trace") or {}).get("excluded_doc_ids") or []
                    ),
                    "input_tokens": (record.get("usage") or {}).get("input_tokens"),
                    "output_tokens": (record.get("usage") or {}).get("output_tokens"),
                    "latency_ms": (record.get("usage") or {}).get("latency_ms"),
                    "estimated_cost_usd": record.get("estimated_cost_usd"),
                    "prompt_sha256": record.get("prompt_sha256"),
                    "started_utc": record.get("started_utc"),
                }
            )
