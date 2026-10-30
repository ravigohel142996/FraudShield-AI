"""Command-line entry point.

    python -m src.runner validate                # schema + semantic validation only
    python -m src.runner preflight               # show planned runs and cost estimate
    python -m src.runner credentials             # which provider keys are present (names only)
    python -m src.runner run --live              # real experiment (needs keys + budget)
    python -m src.runner run --pipeline-check    # offline stub, labelled, not a model result
    python -m src.runner report --dir results    # re-render the markdown report

The `run` command defaults to refusing to do anything expensive: `--live` must be passed
explicitly, and even then `budget.allow_live_calls` must be true in the config.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .evaluation_runner import BudgetExceeded, preflight_estimate, run_suite
from .model_provider import describe_credentials, get_provider
from .report_generator import export_bundle
from .settings import RESULTS_DIR, RunSettings, load_benchmark_config, load_policy
from .task_loader import load_tasks
from .task_validator import validate_all


def _load():
    cfg = load_benchmark_config()
    settings = RunSettings.from_config(cfg)
    tasks = load_tasks()
    return cfg, settings, tasks


def cmd_validate(args: argparse.Namespace) -> int:
    _, _, tasks = _load()
    errors, warnings = validate_all(tasks)
    print(f"Loaded {len(tasks)} tasks from tasks/")
    for task in tasks:
        print(f"  {task['task_id']}  {task.get('difficulty', '?'):<6} "
              f"{'/'.join(task.get('track', [])):<4} {task.get('category')}  — {task.get('title')}")
    if warnings:
        print("\nWarnings:")
        for tid, items in warnings.items():
            for item in items:
                print(f"  {tid}: {item}")
    if errors:
        print("\nERRORS:")
        for tid, items in errors.items():
            for item in items:
                print(f"  {tid}: {item}")
        return 1
    print("\nAll tasks valid.")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    cfg, settings, tasks = _load()
    models = settings.models
    if not models:
        print("No models configured in config/benchmark.yaml (run.models is empty).")
        print("Add entries such as:")
        print("  run:\n    models:\n      - provider: openai\n        model: gpt-4o-mini-2024-07-18")
        return 0
    estimate = preflight_estimate(tasks, models, settings)
    print(f"Planned runs: {estimate['runs_planned']}")
    print(f"Estimated worst-case cost: ${estimate['estimated_total_cost_usd']:.4f} (ESTIMATE)")
    print(f"Approved limit: ${settings.max_total_cost_usd:.2f}  "
          f"allow_live_calls={settings.allow_live_calls}")
    for entry in estimate["models"]:
        print(f"  {entry['provider']}:{entry['model']} available={entry['available']} "
              f"({entry['credential']}) est=${entry['estimated_cost_usd']}")
    return 0


def cmd_credentials(args: argparse.Namespace) -> int:
    print("Provider credential status (names only; values are never read into output):")
    for row in describe_credentials():
        print(f"  {row['provider']:<10} {row['env_var']:<20} {row['status']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    cfg, settings, tasks = _load()

    if args.pipeline_check:
        out_dir = RESULTS_DIR / "validation"
        settings = RunSettings(**{**settings.__dict__, "models": [
            {"provider": "stub", "model": "offline-pipeline-validation-stub"}
        ], "repetitions": 1})
        print("=" * 78)
        print("PIPELINE VALIDATION MODE — deterministic offline stub, no API calls.")
        print("Output is NOT a model experiment and is written to results/validation/.")
        print("=" * 78)
        bundle = run_suite(tasks, settings.models, settings, run_label=args.label or "pipeline-check",
                           out_dir=out_dir, provider_class="pipeline_validation_stub",
                           check_budget_for_live=False)
        paths = export_bundle(out_dir, bundle["summary"], bundle["records"])
        for name, path in paths.items():
            print(f"wrote {name}: {path}")
        return 0

    if not args.live:
        print("Refusing to spend money: pass --live to run a real experiment, or "
              "--pipeline-check for the offline wiring test.")
        return 2
    if not settings.models:
        print("No models configured in config/benchmark.yaml. Nothing to run.")
        return 2

    try:
        bundle = run_suite(tasks, settings.models, settings,
                           run_label=args.label or "live",
                           out_dir=Path(args.dir) if args.dir else RESULTS_DIR,
                           provider_class="llm_api", check_budget_for_live=True)
    except BudgetExceeded as exc:
        print(f"BLOCKED: {exc}")
        return 3

    out_dir = Path(args.dir) if args.dir else RESULTS_DIR
    paths = export_bundle(out_dir, bundle["summary"], bundle["records"])
    print(f"\nWrote {len(bundle['records'])} run records.")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    import json

    out_dir = Path(args.dir)
    summary_path = out_dir / "summary.json"
    raw_path = out_dir / "raw_outputs.jsonl"
    if not summary_path.exists() or not raw_path.exists():
        print(f"missing {summary_path} or {raw_path}")
        return 2
    summary = json.loads(summary_path.read_text())
    records = [json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]
    for name, path in export_bundle(out_dir, summary, records).items():
        print(f"wrote {name}: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ragshield", description="RAGShield Eval runner")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="validate task definitions").set_defaults(func=cmd_validate)
    sub.add_parser("preflight", help="cost/availability preflight").set_defaults(func=cmd_preflight)
    sub.add_parser("credentials", help="provider credential presence").set_defaults(func=cmd_credentials)

    run_parser = sub.add_parser("run", help="execute the benchmark")
    run_parser.add_argument("--live", action="store_true", help="perform real API calls")
    run_parser.add_argument("--pipeline-check", action="store_true", help="offline wiring test")
    run_parser.add_argument("--label", default="", help="run label recorded in the manifest")
    run_parser.add_argument("--dir", default="", help="output directory")
    run_parser.set_defaults(func=cmd_run)

    report_parser = sub.add_parser("report", help="re-render reports for an existing run")
    report_parser.add_argument("--dir", default=str(RESULTS_DIR))
    report_parser.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
