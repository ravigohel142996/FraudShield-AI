"""Human-readable experiment report generation (Markdown).

The generator refuses to describe pipeline-validation artefacts as model results; the
banner is driven by the manifest flag, not by the caller's wishful thinking.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .settings import dump_json

_METRIC_LABELS = {
    "task_accuracy": "Task accuracy",
    "task_accuracy_first_repetition": "Task accuracy (repetition 1 only)",
    "injection_resistance": "Injection resistance",
    "canary_leakage_rate": "Canary leakage rate (lower is better)",
    "unauthorized_retrieval_rate": "Unauthorized retrieval rate (lower is better)",
    "citation_correctness": "Citation correctness",
    "grounding_correctness": "Grounding correctness",
    "false_refusal_rate": "False refusal rate (lower is better)",
    "appropriate_abstention_rate": "Appropriate abstention rate",
}


def _fmt(entry: Dict[str, Any]) -> str:
    if not entry or entry.get("value") is None:
        return "n/a (denominator 0)"
    return f"{entry['value'] * 100:.1f}% ({entry['numerator']}/{entry['denominator']})"


def _banner(summary: Dict[str, Any]) -> List[str]:
    if summary.get("counts_as_model_experiment"):
        return [
            "> **Status: REAL MODEL EXPERIMENT.** Every response below was produced by a",
            "> live provider API call and is stored verbatim in `raw_outputs.jsonl`.",
        ]
    return [
        "> ## ⚠️ PIPELINE VALIDATION — NOT A MODEL EXPERIMENT",
        ">",
        "> The provider class for this run was a deterministic offline stub whose only purpose",
        "> is to prove that retrieval, authorization, prompting, grading and reporting are wired",
        "> together correctly. **No score in this document is a measurement of any language",
        "> model.** Do not cite these numbers as findings. Real results require a provider API",
        "> key and an approved spending limit; see README §5.",
    ]


def render_markdown_report(summary: Dict[str, Any], records: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append(f"# RAGShield Eval — Experiment report: `{summary.get('run_label')}`")
    lines.append("")
    lines.extend(_banner(summary))
    lines.append("")
    lines.append(f"- Generated: {summary.get('created_utc')}")
    lines.append(f"- Provider class: `{summary.get('provider_class')}`")
    lines.append(f"- Runs total: {summary.get('runs_total')}")
    lines.append(f"- Runs scored: {summary.get('runs_scored')}")
    lines.append(f"- API errors: {summary.get('runs_api_error')}")
    cost = summary.get("estimated_total_cost_usd")
    lines.append(f"- Estimated cost: ${cost:.4f} (estimate only, not a bill)" if cost is not None else "- Estimated cost: n/a")
    lines.append("")

    for model_key, payload in (summary.get("models") or {}).items():
        metrics = payload.get("metrics") or {}
        lines.append(f"## Model `{model_key}`")
        lines.append("")
        lines.append("| Metric | Value (numerator/denominator) |")
        lines.append("|---|---|")
        for key, label in _METRIC_LABELS.items():
            lines.append(f"| {label} | {_fmt(metrics.get(key))} |")
        critical = metrics.get("critical_security_failures") or {}
        lines.append(
            f"| Critical security failures | {critical.get('count', 0)} / {critical.get('denominator', 0)} runs"
            f" ({', '.join(critical.get('task_ids') or []) or 'none'}) |"
        )
        weighted = payload.get("weighted") or {}
        lines.append("")
        lines.append(
            f"Weighted composite: **{weighted.get('weighted_score')}** "
            f"(weights applied: {weighted.get('weights_applied')}). "
            "The composite is context, never a substitute for the per-metric table."
        )
        lines.append("")
        lines.append("### Per-task results")
        lines.append("")
        lines.append("| Task | Runs | Passed | Pass rate | Critical failures | Failed checks |")
        lines.append("|---|---|---|---|---|---|")
        for task_id, entry in (payload.get("per_task") or {}).items():
            failed = ", ".join(f"{k}×{v}" for k, v in (entry.get("failed_checks") or {}).items()) or "—"
            lines.append(
                f"| {task_id} | {entry.get('runs')} | {entry.get('passed')} | "
                f"{(entry.get('pass_rate') or 0) * 100:.0f}% | {entry.get('critical')} | {failed} |"
            )
        lines.append("")

    # Failure excerpts — verbatim, never paraphrased
    failing = [r for r in records if r.get("counts_as_scored") and r.get("grading", {}).get("failed_checks")]
    lines.append("## Failure excerpts (verbatim)")
    lines.append("")
    if not failing:
        lines.append("No scored failures in this run.")
    else:
        for record in failing[:40]:
            lines.append(f"### {record['task_id']} — `{record['provider']}:{record['model_id']}` "
                         f"(repetition {record.get('repetition')})")
            lines.append("")
            lines.append(f"Failed checks: `{', '.join(record['grading']['failed_checks'])}`")
            if record.get("leaked_canaries"):
                lines.append(f"Leaked canaries: `{', '.join(record['leaked_canaries'])}`")
            lines.append("")
            lines.append("```text")
            lines.append((record.get("response_text") or "").strip()[:1200])
            lines.append("```")
            lines.append("")
    if len(failing) > 40:
        lines.append(f"_(truncated: {len(failing) - 40} further failing runs in `raw_outputs.jsonl`)_")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_report(out_dir: Path, summary: Dict[str, Any], records: List[Dict[str, Any]]) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.md"
    path.write_text(render_markdown_report(summary, records), encoding="utf-8")
    return path


def export_bundle(out_dir: Path, summary: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Path]:
    out_dir = Path(out_dir)
    written = {"report": write_report(out_dir, summary, records)}
    dump_json(out_dir / "dashboard_data.json", {"summary": summary,
                                               "records": [_dashboard_record(r) for r in records]})
    written["dashboard_data"] = out_dir / "dashboard_data.json"
    return written


def _dashboard_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Trim records for dashboard payload size while keeping everything shown in the UI."""
    keep = {
        "task_id", "task_category", "task_difficulty", "track", "provider", "model_id",
        "provider_class", "repetition", "status", "counts_as_scored", "response_text",
        "grading", "leaked_canaries", "prompt_doc_ids", "retrieval_trace", "usage",
        "prompt_sha256", "started_utc", "estimated_cost_usd", "error", "run_label",
    }
    return {k: v for k, v in record.items() if k in keep}
