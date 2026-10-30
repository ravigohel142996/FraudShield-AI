"""Path resolution and config loading. No third-party dependencies required."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = PROJECT_ROOT / "tasks"
CONFIG_DIR = PROJECT_ROOT / "config"
RESULTS_DIR = PROJECT_ROOT / "results"


def _parse_scalar(value: str) -> Any:
    raw = value.strip()
    if raw in ("", "~", "null"):
        return None
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    if raw.startswith(("'", '"')) and raw.endswith(("'", '"')) and len(raw) >= 2:
        return raw[1:-1]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [] if not inner else [_parse_scalar(p) for p in inner.split(",")]
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def load_yaml(path: Path) -> Dict[str, Any]:
    """Minimal YAML reader for this project's flat config files.

    Deliberately dependency-free so the benchmark core runs in an environment that has
    nothing but Python. Supports nested mappings by indentation, comments, lists in
    [a, b] form, quoted strings and a single trailing '|' block scalar.
    If PyYAML is installed we prefer it (better fidelity).
    """
    text = path.read_text(encoding="utf-8")
    try:  # pragma: no cover - optional path
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        pass
    return _mini_yaml(text)


def _mini_yaml(text: str) -> Dict[str, Any]:
    root: Dict[str, Any] = {}
    # stack of (indent, dict)
    stack: List[tuple] = [(-1, root)]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value in ("|", ">", "|-"):
            block: List[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip(" "))) <= indent:
                    break
                block.append(nxt)
                i += 1
            # strip common indentation
            non_empty = [b for b in block if b.strip()]
            cut = min((len(b) - len(b.lstrip(" ")) for b in non_empty), default=0)
            parent[key] = "\n".join(b[cut:] if b.strip() else "" for b in block).strip("\n") + "\n"
        elif value == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return root


def load_policy() -> Dict[str, Any]:
    return load_yaml(CONFIG_DIR / "policy.yaml")


def load_benchmark_config() -> Dict[str, Any]:
    return load_yaml(CONFIG_DIR / "benchmark.yaml")


def env_or_empty(name: str) -> str:
    """Read a secret without ever logging it."""
    return (os.environ.get(name) or "").strip()


@dataclass
class RunSettings:
    models: List[Dict[str, str]] = field(default_factory=list)
    repetitions: int = 3
    temperature: float = 0.0
    max_output_tokens: int = 700
    timeout_seconds: int = 60
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0
    allow_live_calls: bool = False
    max_total_cost_usd: float = 2.0

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "RunSettings":
        run = cfg.get("run") or {}
        budget = cfg.get("budget") or {}
        models = run.get("models") or []
        clean_models = []
        for m in models:
            if isinstance(m, dict) and m.get("provider") and m.get("model"):
                clean_models.append(
                    {"provider": str(m["provider"]), "model": str(m["model"])}
                )
        return cls(
            models=clean_models,
            repetitions=int(run.get("repetitions", 3) or 3),
            temperature=float(run.get("temperature", 0.0) or 0.0),
            max_output_tokens=int(run.get("max_output_tokens", 700) or 700),
            timeout_seconds=int(run.get("timeout_seconds", 60) or 60),
            max_retries=int(run.get("max_retries", 2) or 0),
            retry_backoff_seconds=float(run.get("retry_backoff_seconds", 2.0) or 0.0),
            allow_live_calls=bool(budget.get("allow_live_calls", False)),
            max_total_cost_usd=float(budget.get("max_total_cost_usd", 0.0) or 0.0),
        )


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
