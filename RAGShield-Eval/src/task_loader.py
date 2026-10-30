"""Load machine-readable benchmark tasks from tasks/*.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .settings import TASKS_DIR


def load_task_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_tasks(tasks_dir: Path | None = None) -> List[Dict[str, Any]]:
    """Load every task file, sorted by task_id for deterministic ordering."""
    directory = Path(tasks_dir) if tasks_dir else TASKS_DIR
    if not directory.exists():
        raise FileNotFoundError(f"tasks directory not found: {directory}")
    tasks: List[Dict[str, Any]] = []
    for path in sorted(directory.glob("task_*.json")):
        task = load_task_file(path)
        task["_source_file"] = path.name
        tasks.append(task)
    tasks.sort(key=lambda t: str(t.get("task_id", "")))
    if not tasks:
        raise FileNotFoundError(f"no task_*.json files found in {directory}")
    return tasks


def load_task(task_id: str, tasks_dir: Path | None = None) -> Dict[str, Any]:
    for task in load_tasks(tasks_dir):
        if task["task_id"] == task_id:
            return task
    raise KeyError(f"task {task_id!r} not found")


def documents_by_id(task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {doc["doc_id"]: doc for doc in task["documents"]}
