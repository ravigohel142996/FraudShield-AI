"""RAGShield Eval — evaluation dashboard (Streamlit).

Run with:  streamlit run dashboard/app.py

Hard rules enforced in the UI:
  * If a run directory's manifest says `counts_as_model_experiment: false`, every page
    carries a loud banner and no metric is presented as a model finding.
  * If no run directories exist, the dashboard shows an honest empty state with the
    exact command needed to produce results. It never invents data to fill a chart.
  * Only artefacts written by src/evaluation_runner.py are displayed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.task_loader import load_tasks  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "results"

st.set_page_config(
    page_title="RAGShield Eval",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
  .block-container {padding-top: 2rem;}
  .rs-badge {display:inline-block;padding:0.35rem 0.8rem;border-radius:0.5rem;
             font-size:0.85rem;font-weight:600;letter-spacing:0.02em;}
  .rs-real {background:#0f5132;color:#d1e7dd;}
  .rs-stub {background:#842029;color:#f8d7da;}
  .rs-empty {background:#332701;color:#fff3cd;}
  .rs-card {border:1px solid rgba(128,128,128,0.25);border-radius:0.75rem;
            padding:1rem 1.1rem;height:100%;}
  .rs-kpi {font-size:1.9rem;font-weight:700;line-height:1.1;}
  .rs-sub {font-size:0.8rem;opacity:0.75;}
  .rs-mono {font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:0.82rem;}
  h1, h2, h3 {letter-spacing:-0.01em;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- data
def find_run_dirs() -> list[Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted([p for p in RESULTS_DIR.iterdir() if p.is_dir() and (p / "summary.json").exists()])


@st.cache_data(show_spinner=False)
def load_run(run_dir: str) -> dict:
    base = Path(run_dir)
    summary = json.loads((base / "summary.json").read_text())
    manifest_path = base / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    records = []
    raw = base / "raw_outputs.jsonl"
    if raw.exists():
        records = [json.loads(line) for line in raw.read_text().splitlines() if line.strip()]
    return {"summary": summary, "manifest": manifest, "records": records}


@st.cache_data(show_spinner=False)
def tasks_frame() -> pd.DataFrame:
    rows = []
    for task in load_tasks():
        rows.append(
            {
                "task_id": task["task_id"],
                "title": task["title"],
                "category": task["category"],
                "track": "/".join(task["track"]),
                "difficulty": task["difficulty"],
                "documents": len(task["documents"]),
                "trust_labels": ", ".join(sorted({d.get("trust_label", "?") for d in task["documents"]})),
                "has_canary": any("CANARY_" in d.get("content", "") for d in task["documents"]),
                "checks": ", ".join(task["grading"]["checks"]),
                "user_query": task["user_query"],
                "rationale": task["security_rationale"],
                "ground_truth": task["ground_truth"],
                "expected_failures": task["expected_failure_patterns"],
            }
        )
    return pd.DataFrame(rows)


def pct(metric: dict | None) -> str:
    if not metric or metric.get("value") is None:
        return "n/a"
    return f"{metric['value'] * 100:.1f}%"


def denom(metric: dict | None) -> str:
    if not metric:
        return ""
    return f"{metric.get('numerator', 0)}/{metric.get('denominator', 0)}"


def status_badge(summary: dict) -> str:
    if summary.get("counts_as_model_experiment"):
        return '<span class="rs-badge rs-real">● REAL MODEL EXPERIMENT</span>'
    return '<span class="rs-badge rs-stub">⚠ PIPELINE VALIDATION — NOT MODEL RESULTS</span>'


def kpi(label: str, value: str, sub: str = "") -> str:
    return (
        f'<div class="rs-card"><div class="rs-sub">{label}</div>'
        f'<div class="rs-kpi">{value}</div><div class="rs-sub">{sub}</div></div>'
    )


# --------------------------------------------------------------------------- sidebar
st.sidebar.title("🛡️ RAGShield Eval")
st.sidebar.caption("Indirect prompt injection & retrieval authorisation benchmark")

run_dirs = find_run_dirs()
selected = None
if run_dirs:
    labels = {}
    for directory in run_dirs:
        try:
            s = json.loads((directory / "summary.json").read_text())
            flag = "REAL" if s.get("counts_as_model_experiment") else "stub"
            labels[f"{directory.name}  ·  {s.get('run_label', '?')}  ·  {flag}"] = directory
        except Exception:
            labels[directory.name] = directory
    choice = st.sidebar.radio("Run artefacts", list(labels), index=0)
    selected = labels[choice]
    st.sidebar.divider()

st.sidebar.markdown("**Reproduce**")
st.sidebar.code(
    "python -m src.runner validate\n"
    "python -m src.runner credentials\n"
    "python -m src.runner preflight\n"
    "python -m src.runner run --live",
    language="bash",
)
st.sidebar.caption(
    "A live run needs a provider API key and an approved spending limit in "
    "config/benchmark.yaml."
)

# --------------------------------------------------------------------------- empty state
if selected is None:
    st.title("RAGShield Eval")
    st.markdown('<span class="rs-badge rs-empty">● NO RUN ARTEFACTS FOUND</span>', unsafe_allow_html=True)
    st.write("")
    st.info(
        "There are no experiment artefacts in `results/` yet, so this dashboard has nothing "
        "to display. It deliberately shows no placeholder numbers: any chart here would be "
        "invented. Generate real results with a provider key, or inspect the wiring with the "
        "offline stub (which is labelled as such and never counted as a model result)."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Offline wiring check (no API key, no cost)**")
        st.code("python -m src.runner run --pipeline-check", language="bash")
    with col_b:
        st.markdown("**Real experiment (needs key + approved budget)**")
        st.code("python -m src.runner run --live --label pilot", language="bash")
    st.divider()
    st.subheader("Benchmark suite (definitions are available without running anything)")
    frame = tasks_frame()
    st.dataframe(
        frame[["task_id", "title", "category", "track", "difficulty", "documents", "checks"]],
        width="stretch",
        hide_index=True,
    )
    st.stop()

# --------------------------------------------------------------------------- load
bundle = load_run(str(selected))
summary, manifest, records = bundle["summary"], bundle["manifest"], bundle["records"]
is_real = bool(summary.get("counts_as_model_experiment"))
metrics_by_model = summary.get("models") or {}

st.title("RAGShield Eval")
st.markdown(status_badge(summary), unsafe_allow_html=True)
if not is_real:
    st.error(
        "**These numbers are not model results.** This run used the deterministic offline "
        "stub provider to prove the retrieval → authorisation → prompting → grading → "
        "reporting pipeline works. No language model was called. Do not cite any figure on "
        "this page as a finding."
    )
else:
    st.caption(
        f"Run `{summary.get('run_label')}` · created {summary.get('created_utc')} · "
        f"models: {len(metrics_by_model)} · runs: {summary.get('runs_total')}"
    )

tabs = st.tabs(
    [
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
)
(
    tab_overview,
    tab_tasks,
    tab_models,
    tab_runs,
    tab_scoring,
    tab_security,
    tab_authz,
    tab_repro,
    tab_export,
) = tabs

scored = [r for r in records if r.get("counts_as_scored")]

# --------------------------------------------------------------------------- overview
with tab_overview:
    any_metrics = next(iter(metrics_by_model.values()), {}).get("metrics", {}) if metrics_by_model else {}
    critical = (any_metrics.get("critical_security_failures") or {}).get("count", 0)
    cols = st.columns(5)
    cols[0].markdown(kpi("Benchmark tasks", str(len(tasks_frame())), "8 designed scenarios"), unsafe_allow_html=True)
    cols[1].markdown(
        kpi("Models tested", str(len(metrics_by_model)), "real" if is_real else "stub only"),
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        kpi("Runs", str(summary.get("runs_total", 0)),
            f"{summary.get('runs_api_error', 0)} API errors"),
        unsafe_allow_html=True,
    )
    cols[3].markdown(
        kpi("Scored runs", str(summary.get("runs_scored", 0)),
            "stub output is never scored" if not is_real else "graded responses"),
        unsafe_allow_html=True,
    )
    cols[4].markdown(
        kpi("Critical security failures", str(critical), "not averaged away"),
        unsafe_allow_html=True,
    )
    st.write("")
    if not is_real:
        st.warning(
            "Pipeline validation run: retrieval traces, prompt hashes and grading wiring are "
            "real, but the responses came from a stub. Metrics are not model measurements."
        )
    rows = []
    for model_key, payload in metrics_by_model.items():
        m = payload.get("metrics", {})
        rows.append(
            {
                "model": model_key,
                "task_accuracy": pct(m.get("task_accuracy")),
                "injection_resistance": pct(m.get("injection_resistance")),
                "canary_leakage": pct(m.get("canary_leakage_rate")),
                "citation_correctness": pct(m.get("citation_correctness")),
                "false_refusal": pct(m.get("false_refusal_rate")),
            }
        )
    if rows:
        st.subheader("Headline metrics")
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.caption("Full denominators are on the Scoring tab. `n/a` means the denominator was zero.")
    st.subheader("What this benchmark measures")
    st.markdown(
        "- **Track A — model behaviour.** Does the model treat retrieved text as data, or as instructions?\n"
        "- **Track B — retrieval authorisation.** Does the application ever place a document the "
        "principal may not read into the model's context? This verdict comes from the retrieval "
        "trace, not from the response: a polite refusal does not make an unsafe retriever safe."
    )

# --------------------------------------------------------------------------- tasks
with tab_tasks:
    frame = tasks_frame()
    st.subheader("Benchmark task explorer")
    filters = st.columns(3)
    track_filter = filters[0].multiselect("Track", ["A", "B"], default=["A", "B"])
    diff_filter = filters[1].multiselect("Difficulty", ["easy", "medium", "hard"],
                                        default=["easy", "medium", "hard"])
    category_filter = filters[2].multiselect("Category", sorted(frame["category"].unique()),
                                             default=sorted(frame["category"].unique()))
    view = frame[
        frame["track"].apply(lambda t: any(x in track_filter for x in t.split("/")))
        & frame["difficulty"].isin(diff_filter)
        & frame["category"].isin(category_filter)
    ]
    st.dataframe(
        view[["task_id", "title", "category", "track", "difficulty", "documents", "checks"]],
        width="stretch",
        hide_index=True,
    )
    picked = st.selectbox("Inspect task", view["task_id"].tolist() if not view.empty else [])
    if picked:
        row = frame[frame["task_id"] == picked].iloc[0]
        task = next(t for t in load_tasks() if t["task_id"] == picked)
        st.markdown(f"### {picked} — {row['title']}")
        left, right = st.columns([3, 2])
        with left:
            st.markdown(f"**User query**\n\n> {task['user_query']}")
            st.markdown(f"**Security rationale**\n\n{task['security_rationale']}")
            st.markdown(f"**Ground truth**\n\n{task['ground_truth']}")
        with right:
            st.markdown(f"**Track** `{row['track']}` · **Difficulty** `{row['difficulty']}`")
            st.markdown(f"**Requesting principal** `{task['requesting_principal']}`")
            st.markdown("**Expected failure patterns**")
            for pattern in task["expected_failure_patterns"]:
                st.markdown(f"- {pattern}")
        st.markdown("#### Retrieval documents")
        for doc in task["documents"]:
            acl = doc.get("acl")
            acl_note = "**NO ACL METADATA → deny by default**" if not acl else f"`{acl.get('required_permissions')}`"
            with st.expander(f"{doc['doc_id']} · {doc.get('trust_label')} · tenant {doc['tenant']}"):
                st.caption(f"authority={doc.get('authority')} · permissions={acl_note}")
                st.code(doc["content"], language="text")

# --------------------------------------------------------------------------- models
with tab_models:
    st.subheader("Model comparison")
    if not is_real:
        st.info("No real model runs exist. Comparison will populate automatically once "
                "`python -m src.runner run --live` has been executed.")
    metric_keys = [
        "task_accuracy", "injection_resistance", "canary_leakage_rate",
        "unauthorized_retrieval_rate", "citation_correctness", "grounding_correctness",
        "false_refusal_rate", "appropriate_abstention_rate",
    ]
    table = []
    for model_key, payload in metrics_by_model.items():
        m = payload.get("metrics", {})
        row = {"model": model_key}
        for key in metric_keys:
            row[key] = pct(m.get(key))
        row["weighted"] = (payload.get("weighted") or {}).get("weighted_score")
        table.append(row)
    if table:
        st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)
        st.caption("Lower is better for canary_leakage_rate, unauthorized_retrieval_rate and "
                   "false_refusal_rate.")
    if metrics_by_model:
        model_key = st.selectbox("Per-task detail", list(metrics_by_model))
        per_task = metrics_by_model[model_key].get("per_task") or {}
        if per_task:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "task": tid,
                            "runs": v["runs"],
                            "passed": v["passed"],
                            "pass_rate": v.get("pass_rate"),
                            "critical": v.get("critical"),
                            "failed_checks": ", ".join(f"{k}×{c}" for k, c in (v.get("failed_checks") or {}).items()) or "—",
                        }
                        for tid, v in per_task.items()
                    ]
                ),
                width="stretch",
                hide_index=True,
            )

# --------------------------------------------------------------------------- runs
with tab_runs:
    st.subheader("Runs and raw outputs")
    if not records:
        st.info("No run records in this directory.")
    else:
        table_rows = []
        for record in records:
            grading = record.get("grading") or {}
            table_rows.append(
                {
                    "task": record.get("task_id"),
                    "model": f"{record.get('provider')}:{record.get('model_id')}",
                    "rep": record.get("repetition"),
                    "status": record.get("status"),
                    "scored": record.get("counts_as_scored"),
                    "passed": grading.get("task_passed"),
                    "failed_checks": ", ".join(grading.get("failed_checks") or []),
                    "canaries": ", ".join(record.get("leaked_canaries") or []),
                    "latency_ms": (record.get("usage") or {}).get("latency_ms"),
                }
            )
        st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)
        keys = [f"{r.get('task_id')} · {r.get('model_id')} · rep {r.get('repetition')}" for r in records]
        index = st.selectbox("Open run", range(len(records)), format_func=lambda i: keys[i])
        record = records[index]
        st.markdown(f"**Prompt SHA-256** `{record.get('prompt_sha256')}`")
        st.markdown(f"**Documents in context** `{record.get('prompt_doc_ids')}`")
        trace = record.get("retrieval_trace") or {}
        st.markdown(f"**Withheld by authorisation** `{trace.get('excluded_doc_ids')}`")
        st.markdown("**Response (verbatim)**")
        st.code(record.get("response_text") or record.get("error") or "(empty)", language="text")
        grading = record.get("grading")
        if grading:
            st.markdown("**Grading**")
            for check in grading.get("checks", []):
                icon = "✅" if check["passed"] else "❌"
                st.markdown(f"{icon} `{check['check']}` — {check.get('detail', '')}")

# --------------------------------------------------------------------------- scoring
with tab_scoring:
    st.subheader("Scoring breakdown")
    st.caption("Every metric is shown with its explicit denominator. A zero denominator is "
               "reported as n/a, never as 0% or 100%.")
    metric_labels = {
        "task_accuracy": "Task accuracy",
        "task_accuracy_first_repetition": "Task accuracy (rep 1)",
        "injection_resistance": "Injection resistance",
        "canary_leakage_rate": "Canary leakage (lower better)",
        "unauthorized_retrieval_rate": "Unauthorized retrieval (lower better)",
        "citation_correctness": "Citation correctness",
        "grounding_correctness": "Grounding correctness",
        "false_refusal_rate": "False refusal (lower better)",
        "appropriate_abstention_rate": "Appropriate abstention",
    }
    for model_key, payload in metrics_by_model.items():
        m = payload.get("metrics", {})
        st.markdown(f"#### `{model_key}`")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "metric": label,
                        "value": pct(m.get(key)),
                        "numerator/denominator": denom(m.get(key)),
                        "status": (m.get(key) or {}).get("status"),
                    }
                    for key, label in metric_labels.items()
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        critical = m.get("critical_security_failures") or {}
        st.markdown(
            f"**Critical security failures:** {critical.get('count', 0)} / "
            f"{critical.get('denominator', 0)} runs"
            + (f" — tasks {', '.join(critical.get('task_ids') or [])}" if critical.get("task_ids") else "")
        )
        weighted = payload.get("weighted") or {}
        st.markdown(
            f"**Weighted composite:** {weighted.get('weighted_score')} "
            f"(weights applied {weighted.get('weights_applied')})"
        )
        st.caption(weighted.get("warning", ""))
        with st.expander("Metric denominators map"):
            st.json({k: m.get(k) for k in m if k.startswith("task_ids_in_")})

# --------------------------------------------------------------------------- security
with tab_security:
    st.subheader("Security failure analysis")
    failing = [r for r in scored if (r.get("grading") or {}).get("critical_security_failure")]
    if not is_real:
        st.info("Security findings require real model responses. This run is a pipeline check.")
    if not failing:
        st.success("No critical (forbidden-content) failures recorded in scored runs of this artefact set.")
    for record in failing[:20]:
        st.markdown(
            f"#### {record['task_id']} · `{record.get('provider')}:{record.get('model_id')}` · "
            f"rep {record.get('repetition')}"
        )
        st.markdown(f"Failed checks: `{', '.join(record['grading']['failed_checks'])}`")
        if record.get("leaked_canaries"):
            st.error(f"Protected canary disclosed: {', '.join(record['leaked_canaries'])}")
        for check in record["grading"]["checks"]:
            if not check["passed"] and check["check"] in ("forbidden_strings", "contextual_forbidden"):
                st.json(check.get("violations") or [])
        st.code((record.get("response_text") or "")[:1500], language="text")

# --------------------------------------------------------------------------- authz
with tab_authz:
    st.subheader("Retrieval authorisation (Track B)")
    st.caption(
        "Computed from the retrieval trace only. Each row is a document the ranking step "
        "produced and the authorisation engine then judged, independently of the model."
    )
    authz_rows = []
    for record in records:
        trace = record.get("retrieval_trace") or {}
        for decision in trace.get("authorization_decisions") or []:
            authz_rows.append(
                {
                    "task": record.get("task_id"),
                    "doc": decision.get("doc_id"),
                    "allowed": decision.get("allowed"),
                    "rule": decision.get("rule"),
                    "reason": decision.get("reason"),
                    "in_prompt": decision.get("doc_id") in (trace.get("prompt_doc_ids") or []),
                }
            )
    if authz_rows:
        frame = pd.DataFrame(authz_rows)
        st.dataframe(frame.drop_duplicates(subset=["task", "doc"]), width="stretch", hide_index=True)
        denied = frame[~frame["allowed"].astype(bool)]
        st.markdown(f"**Documents denied:** {len(denied.drop_duplicates(subset=['task','doc']))}")
        leaked = frame[(~frame["allowed"].astype(bool)) & (frame["in_prompt"])]
        if leaked.empty:
            st.success("Invariant holds: no denied document reached the prompt.")
        else:
            st.error(f"Track B failure: denied documents present in prompt: "
                     f"{leaked['doc'].unique().tolist()}")
    else:
        st.info("No retrieval traces in this artefact set.")

# --------------------------------------------------------------------------- repro
with tab_repro:
    st.subheader("Reproducibility and experiment metadata")
    if manifest:
        env = manifest.get("environment", {})
        cols = st.columns(4)
        cols[0].metric("Python", env.get("python_version", "?"))
        cols[1].metric("Tasks", manifest.get("tasks", {}).get("count", "?"))
        cols[2].metric("Policy", manifest.get("policy", {}).get("policy_version", "?"))
        cols[3].metric("Model experiment", str(manifest.get("counts_as_model_experiment")))
        st.markdown(f"**Git commit** `{env.get('git_commit')}` · worktree dirty: `{env.get('git_worktree_dirty')}`")
        st.markdown(f"**Policy SHA-256** `{manifest.get('policy', {}).get('policy_sha256')}`")
        st.markdown(f"**Platform** `{env.get('platform')}`")
        st.markdown(f"**Estimated cost** `{manifest.get('cost', {}).get('estimated_total_usd')}` USD "
                    f"({manifest.get('cost', {}).get('label')})")
        st.json(manifest.get("run_settings", {}))
        with st.expander("Per-task definition hashes"):
            st.json(manifest.get("tasks", {}).get("sha256_per_task", {}))
        with st.expander("Full manifest"):
            st.json(manifest)
    else:
        st.info("No manifest for this run.")

# --------------------------------------------------------------------------- export
with tab_export:
    st.subheader("Exportable reports")
    for name in ("scores.csv", "raw_outputs.jsonl", "summary.json", "experiment_manifest.json",
                 "report.md", "dashboard_data.json"):
        path = Path(selected) / name
        if path.exists():
            st.download_button(
                f"Download {name} ({path.stat().st_size / 1024:.1f} KB)",
                data=path.read_bytes(),
                file_name=f"{selected.name}__{name}",
                key=f"dl-{name}",
            )
    report = Path(selected) / "report.md"
    if report.exists():
        with st.expander("Preview report.md"):
            st.markdown(report.read_text())
