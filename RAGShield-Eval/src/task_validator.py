"""Schema and semantic validation for benchmark tasks.

A benchmark is only as trustworthy as its task definitions, so this validator is
deliberately strict and refuses to load a task suite that violates the design rules.
It is the first thing CI runs.

Structural rules (S*): required fields and types.
Semantic rules (M*): properties a well-formed benchmark task must have, e.g.
  M1  every referenced doc id exists
  M2  every required citation refers to a document actually placed in the prompt
  M3  every forbidden literal appears in the retrieved context only by design
  M4  a canary-forbidding task must expose the canary somewhere in its documents,
      otherwise the task cannot possibly detect leakage
  M5  Track B tasks (those with an ACL-denied candidate) must forbid at least one
      string that only exists in the denied document, so an authorization failure is
      observable in the response as well as in the trace
  M6  a task cannot both require abstention and require a factual answer without saying
      which part is which — enforced by requiring abstention_terms when abstention is on
  M7  each task needs at least one grading check and every check name must exist
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .authorization_engine import authorize_document

VALID_CHECKS = {
    "required_facts",
    "required_citations",
    "forbidden_strings",
    "contextual_forbidden",
    "abstention",
    "false_refusal",
    "citation_validity",
    "unauthorized_retrieval",
}
VALID_TRACKS = {"A", "B"}
REQUIRED_TASK_FIELDS = (
    "task_id",
    "title",
    "category",
    "track",
    "difficulty",
    "user_query",
    "requesting_principal",
    "documents",
    "expected",
    "grading",
    "security_rationale",
    "expected_failure_patterns",
    "ground_truth",
)
REQUIRED_DOC_FIELDS = ("doc_id", "title", "tenant", "trust_label", "content")


def _err(errors: List[str], code: str, message: str) -> None:
    errors.append(f"[{code}] {message}")


def validate_task(task: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings). An empty error list means the task may be used."""
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(task, dict):
        return ["[S0] task is not a JSON object"], []

    for field_name in REQUIRED_TASK_FIELDS:
        if field_name not in task:
            _err(errors, "S1", f"missing required field {field_name!r}")
    if errors:
        return errors, warnings

    tid = task["task_id"]
    if not isinstance(tid, str) or not tid.startswith("T"):
        _err(errors, "S2", f"task_id must be a string like 'T01', got {tid!r}")

    track = task["track"]
    if not isinstance(track, list) or not track or not set(track) <= VALID_TRACKS:
        _err(errors, "S3", f"track must be a non-empty subset of {sorted(VALID_TRACKS)}, got {track!r}")

    principal = task["requesting_principal"]
    for key in ("tenant", "user_id", "permissions"):
        if key not in principal:
            _err(errors, "S4", f"requesting_principal missing {key!r}")
    if not isinstance(principal.get("permissions"), list):
        _err(errors, "S4", "requesting_principal.permissions must be a list")

    docs = task["documents"]
    if not isinstance(docs, list) or not docs:
        _err(errors, "S5", "documents must be a non-empty list")
        return errors, warnings

    seen_ids: set = set()
    for index, doc in enumerate(docs):
        if not isinstance(doc, dict):
            _err(errors, "S5", f"document #{index} is not an object")
            continue
        for key in REQUIRED_DOC_FIELDS:
            if key not in doc:
                _err(errors, "S5", f"document #{index} ({doc.get('doc_id', '?')}) missing {key!r}")
        doc_id = doc.get("doc_id")
        if doc_id in seen_ids:
            _err(errors, "S6", f"duplicate doc_id {doc_id!r}")
        seen_ids.add(doc_id)

    grading = task["grading"]
    checks = grading.get("checks") if isinstance(grading, dict) else None
    if not isinstance(checks, list) or not checks:
        _err(errors, "S7", "grading.checks must be a non-empty list")
        checks = []
    for check in checks:
        if check not in VALID_CHECKS:
            _err(errors, "S7", f"unknown grading check {check!r}; valid: {sorted(VALID_CHECKS)}")

    expected = task["expected"]
    if not isinstance(expected, dict):
        _err(errors, "S8", "expected must be an object")
        return errors, warnings

    # ---------- semantic checks ----------
    retrieval = task.get("retrieval") or {}
    candidate_ids = retrieval.get("candidate_doc_ids") or list(seen_ids)
    for cid in candidate_ids:
        if cid not in seen_ids:
            _err(errors, "M1", f"retrieval.candidate_doc_ids references unknown doc {cid!r}")
    if "retrieval" not in task:
        warnings.append("[M0] no retrieval block; all documents are candidates in file order")
    if "query" not in retrieval:
        warnings.append("[M0] retrieval.query missing; user_query will be used as the search string")

    top_k = int(retrieval.get("top_k", len(candidate_ids)))
    if top_k < 1 or top_k > len(candidate_ids):
        _err(errors, "M1", f"retrieval.top_k={top_k} outside 1..{len(candidate_ids)}")

    # Which documents become the prompt after ranking + authorization?
    from .retrieval_simulator import rank_documents

    doc_map = {d["doc_id"]: d for d in docs if isinstance(d, dict) and d.get("doc_id")}
    query = retrieval.get("query") or task["user_query"]
    ranked = rank_documents(query, [doc_map[c] for c in candidate_ids if c in doc_map])[:top_k]
    prompt_ids = [d["doc_id"] for d in ranked if authorize_document(d, principal).allowed]
    denied_ids = [d["doc_id"] for d in ranked if not authorize_document(d, principal).allowed]
    prompt_text = "\n".join(doc_map[i]["content"] for i in prompt_ids)
    denied_text = "\n".join(doc_map[i]["content"] for i in denied_ids)

    if not prompt_ids:
        _err(errors, "M1", "no document survives authorization; the model would receive no context")

    # M2 — required citations must be citable
    for citation in expected.get("required_citations") or []:
        cited = citation.get("doc_ids") or []
        if not cited:
            _err(errors, "M2", f"required citation {citation.get('id')!r} lists no doc_ids")
        for cid in cited:
            if cid not in seen_ids:
                _err(errors, "M2", f"required citation references unknown doc {cid!r}")
            elif cid not in prompt_ids:
                _err(
                    errors,
                    "M2",
                    f"required citation doc {cid!r} is not in the prompt (prompt={prompt_ids}); "
                    "the model cannot cite it",
                )
        # at least one alternative must be present
        if cited and not any(cid in prompt_ids for cid in cited):
            _err(errors, "M2", f"none of the citation alternatives {cited} are in the prompt")

    # M3/M4/M5 — forbidden strings must give the task discriminating power
    forbidden = expected.get("forbidden_strings") or []
    for entry in forbidden:
        pattern = entry.get("pattern")
        if not pattern:
            _err(errors, "M3", f"forbidden entry {entry.get('id')!r} has no pattern")
            continue
        if entry.get("regex"):
            continue
        lowered = pattern.lower()
        in_all_docs = lowered in "\n".join(d["content"] for d in docs).lower()
        if not in_all_docs:
            _err(
                errors,
                "M4",
                f"forbidden literal {pattern!r} does not appear in any document; "
                "leakage would be indistinguishable from hallucination",
            )
        in_prompt = lowered in prompt_text.lower()
        in_denied = lowered in denied_text.lower() if denied_text else False
        if not in_prompt and not in_denied:
            _err(errors, "M3", f"forbidden literal {pattern!r} is neither in the prompt nor in a denied doc")

    if "B" in (track or []) and denied_ids:
        canaries = [
            e for e in forbidden if not e.get("regex") and e.get("pattern", "").lower() in denied_text.lower()
        ]
        if not canaries:
            _err(
                errors,
                "M5",
                "Track B task denies " + str(denied_ids) + " but forbids no string unique to the denied "
                "document, so a Track B failure would be invisible in the response",
            )
        if "unauthorized_retrieval" not in checks:
            _err(errors, "M5", "Track B task must include the 'unauthorized_retrieval' grading check")

    # M6 — abstention needs terms
    if expected.get("abstention_required"):
        if not expected.get("abstention_terms"):
            _err(errors, "M6", "abstention_required is true but abstention_terms is empty")
        if "abstention" not in checks:
            _err(errors, "M6", "abstention_required is true but 'abstention' is not in grading.checks")

    # M7 — refusal controls
    if expected.get("false_refusal"):
        if not expected.get("refusal_cues"):
            _err(errors, "M7", "false_refusal is true but refusal_cues is empty")
        if "false_refusal" not in checks:
            _err(errors, "M7", "false_refusal is true but 'false_refusal' is not in grading.checks")

    # Control-balance warning: a suite with no benign/answerable task cannot measure over-refusal
    if expected.get("refusal_required") and expected.get("false_refusal"):
        _err(errors, "M7", "a task cannot require both refusal and non-refusal")

    refused_doc_ids = [d for d in denied_ids if d]
    if refused_doc_ids and expected.get("refusal_required") and "required_facts" not in checks:
        warnings.append("[M8] a partial-refusal task should also grade required facts from allowed docs")

    for entry in expected.get("contextual_forbidden") or []:
        if not entry.get("pattern"):
            _err(errors, "M3", f"contextual_forbidden {entry.get('id')!r} has no pattern")
        if "contextual_forbidden" not in checks:
            _err(errors, "M3", f"contextual_forbidden {entry.get('id')!r} present but check not enabled")

    return errors, warnings


def validate_all(tasks: List[Dict[str, Any]]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    all_errors: Dict[str, List[str]] = {}
    all_warnings: Dict[str, List[str]] = {}
    ids: List[str] = []
    for task in tasks:
        tid = str(task.get("task_id", "<unknown>"))
        ids.append(tid)
        errors, warnings = validate_task(task)
        if errors:
            all_errors[tid] = errors
        if warnings:
            all_warnings[tid] = warnings
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        all_errors["<suite>"] = [f"[S9] duplicate task_id values: {sorted(duplicates)}"]
    if not (5 <= len(tasks) <= 10):
        all_errors.setdefault("<suite>", []).append(
            f"[S10] benchmark must contain 5-10 tasks, found {len(tasks)}"
        )
    return all_errors, all_warnings
