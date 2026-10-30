"""Reproducibility helpers: file hashes, environment fingerprint, experiment manifest."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .settings import PROJECT_ROOT


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def git_dirty() -> bool:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return bool(out.stdout.strip())
    except Exception:
        return True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def environment_fingerprint() -> Dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "git_commit": git_commit(),
        "git_worktree_dirty": git_dirty(),
    }


def task_fingerprints(tasks: List[Dict[str, Any]]) -> Dict[str, str]:
    prints = {}
    for task in tasks:
        canonical = json.dumps(task, sort_keys=True)
        prints[task["task_id"]] = sha256_text(canonical)
    return prints


def build_manifest(
    *,
    run_label: str,
    settings_snapshot: Dict[str, Any],
    policy: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    models: List[Dict[str, str]],
    runs_total: int,
    runs_scored: int,
    runs_failed: int,
    estimated_cost_usd: float | None,
    counts_as_model_experiment: bool,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    manifest = {
        "benchmark": "RAGShield Eval",
        "benchmark_version": "1.0.0",
        "run_label": run_label,
        "created_utc": utc_now(),
        "counts_as_model_experiment": counts_as_model_experiment,
        "environment": environment_fingerprint(),
        "policy": {
            "policy_version": policy.get("policy_version"),
            "policy_sha256": sha256_text(str(policy.get("policy_text", ""))),
        },
        "tasks": {
            "count": len(tasks),
            "sha256_per_task": task_fingerprints(tasks),
        },
        "models": models,
        "run_settings": settings_snapshot,
        "counts": {
            "runs_total": runs_total,
            "runs_scored": runs_scored,
            "runs_failed": runs_failed,
        },
        "cost": {
            "estimated_total_usd": estimated_cost_usd,
            "label": "ESTIMATE from config/price table - not a billed amount",
        },
        "environment_note": (
            "Python packages required by the core: none beyond the standard library. "
            "pytest is required only for the test suite; streamlit+pandas only for the dashboard."
        ),
    }
    if extra:
        manifest.update(extra)
    return manifest
