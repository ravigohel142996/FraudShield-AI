# STATE.md — execution log

**Session:** 2026-10-30 · **Branch:** `arena/ab36709c-fraudshield-ai` · **Next action:** §"Resume here"

---

## Status summary

| Item | State |
|---|---|
| Benchmark suite (8 tasks) | **DONE**, validates 8/8 |
| Grading + metrics | **DONE**, 133 tests pass |
| Track B authorization | **DONE**, rules R1–R6 tested per rule |
| Runner / artefacts / manifest | **DONE**, offline pipeline validated |
| Dashboard | **DONE**, 9 tabs, renders without exceptions |
| Documentation | **DONE** (README, audit, methodology ×2, failure analysis, video pack) |
| Submission ZIP | **DONE**, 53 files, 0.14 MB, verified from a clean venv |
| **Real model experiments** | **BLOCKED** — no provider credential, no approved spend, provider hosts unreachable from the sandbox |
| Video | **NOT RECORDED** — script + storyboard ready, requires the participant |

**Nothing in this repository is a model result.** Zero model runs have been executed.

---

## Phase 0 — discovery

Commands: `ls -la`, `git log --oneline`, `gh repo list ravigohel142996 --limit 300`,
`find /home/user -iname "*ragshield*"`, `env | cut -d= -f1 | grep -iE "api|key|token"`.

Findings:
- Connected repo is `FraudShield-AI` — a Streamlit fraud-risk engine, unrelated to RAG.
- **No RAGShield Eval repository exists** (89 public repos checked; workspace search empty).
- No provider credentials in the environment (only `GH_TOKEN`, `GITHUB_TOKEN`).
- No third-party Python packages installed at all (`requests`, `pyyaml`, `pytest`,
  `streamlit`, `pandas` all absent).

Decisions recorded: build RAGShield Eval as a self-contained sub-directory; leave
FraudShield-AI untouched; do not invent a repo URL. Output: `PROJECT_AUDIT.md`.
Raised to the participant: if the RAGShield work lives in another repo, this directory can be
moved wholesale.

## Phase 1–2 — research design and benchmark

- `RESEARCH_METHODOLOGY.md`: hypothesis, two-track design, fixed factors, controls,
  pre-declared limitations, integrity ledger.
- `config/policy.yaml`: one trusted system policy for every task (so cross-task and
  cross-model differences are attributable to the documents).
- 8 tasks, 8 distinct categories, includes a positive control (T08) and partial-denial
  controls (T05/T06/T07).
- `src/task_validator.py`: 10 structural + 8 semantic rules. It immediately caught a real
  defect: T06 declared `top_k=3` with 2 candidate documents. Fixed.

## Phase 3–4 — engine and grading

Modules: `settings`, `task_loader`, `task_validator`, `retrieval_simulator`,
`authorization_engine`, `prompt_builder`, `model_provider`, `graders`, `metrics`,
`evaluation_runner`, `report_generator`, `reproducibility`, `runner`.

Grader defects found **by the tests**, and fixed:
- **E-1** hedge cue supplied by the citation itself (`[DOC-WIKI-SLA-OLD]` contains "wiki") →
  citation brackets stripped before hedge matching.
- **E-2** canary detection scanned only documents owned by other tenants, so T04's planted
  canary was structurally undetectable → explicit `canaries[]` declarations + `protected_canaries()`.
- **E-4** five fixtures had wrong expected verdicts; in each case the grader was right.

See `FAILURE_ANALYSIS.md` §3 for the full write-up.

## Phase 5 — experiments

```
python -m src.runner credentials
  openai     OPENAI_API_KEY    OPENAI_API_KEY is not set
  anthropic  ANTHROPIC_API_KEY ANTHROPIC_API_KEY is not set
  gemini     GEMINI_API_KEY    GEMINI_API_KEY is not set
  groq       GROQ_API_KEY      GROQ_API_KEY is not set
python -m src.runner preflight
  No models configured in config/benchmark.yaml (run.models is empty).
```

Egress allowlist in this sandbox excludes every provider host, so even a key would not have
produced a response. **Result: 0 runs. Reported as BLOCKED, not as a pilot.**

Pipeline validation executed instead (clearly labelled, excluded from metrics):
`python -m src.runner run --pipeline-check` → 8 records, all `counts_as_scored: false`,
artefacts in `results/validation/`.

## Phase 6–7 — failure analysis and dashboard

- `FAILURE_ANALYSIS.md` states the empty case explicitly and documents the 5 evaluator-side
  defects plus the taxonomy and record format for future failures.
- `dashboard/app.py`: 9 tabs (overview, tasks, models, runs/raw, scoring, security,
  retrieval authorisation, reproducibility, export). Red banner on non-experiment runs;
  honest empty state with the exact commands when `results/` is empty.

## Phase 8 — reproducibility (executed, not assumed)

Clean-environment test from the built archive:

```
unzip RAGShield-Eval-micro1-Submission.zip -d /tmp/ragshield-clean     # 53 files
python3 -m venv /tmp/ragshield-clean-venv && pip install -r requirements.txt   # ok
python -m src.runner validate              # All tasks valid.
python -m src.runner credentials           # 4/4 keys absent
python -m src.runner run --pipeline-check  # 8 records written
python -m pytest tests/ -q                 # 133 passed in 0.96s
```

Standard-library-only check with the system interpreter (no third-party packages at all):
`validate` OK, `run --pipeline-check` OK, direct import of loader→retrieval→prompt→grader OK.

## Phase 9–12 — documentation, video pack, packaging

- `README.md` (submission root), `PROJECT_AUDIT.md`, `RESEARCH_METHODOLOGY.md`,
  `SCORING_METHODOLOGY.md`, `FAILURE_ANALYSIS.md`, `docs/TASK_SCHEMA.md`,
  `results/README_RESULTS.md`, `video/{narration,storyboard,recording_checklist}.md`.
- `.env.example` (names only), `requirements.txt` (core = stdlib).
- `scripts/build_submission_zip.py`: allowlist selection, secret-pattern scan (aborts the
  build), README-at-root check, required-file check, size check.

## Modified file list (all new; nothing pre-existing was altered)

```
RAGShield-Eval/  (54 files, incl. generated results/validation/*)
```

Outside `RAGShield-Eval/`: one pointer line added to `FraudShield-AI/README.md`. No existing
file was deleted, renamed or reverted; no force-push; no other branch touched.

---

## Resume here

**Blocked on the participant (in this order):**

1. Decide whether RAGShield Eval belongs in this repository or should move to a dedicated
   one (the directory is portable).
2. Provide **one** provider key and **approve a spending limit**. Then:
   ```bash
   export OPENAI_API_KEY=...            # or ANTHROPIC/GEMINI/GROQ
   # edit config/benchmark.yaml: run.models + budget.allow_live_calls: true
   #                             budget.max_total_cost_usd: <approved>
   python -m src.runner preflight       # prints the worst-case estimate
   python -m src.runner run --live --label pilot     # 1 model × 8 tasks × 1 rep first
   python -m src.runner report --dir results
   ```
   Measured worst-case estimates (`python -m src.runner preflight`, static price table,
   not a bill) — one model, 8 tasks:

   | model | reps | runs | estimate |
   |---|---|---|---|
   | `openai:gpt-4o-mini-2024-07-18` | 1 (pilot) | 8 | **$0.0041** |
   | `openai:gpt-4o-mini-2024-07-18` | 3 | 24 | $0.0123 |
   | `gemini:gemini-2.0-flash` | 3 | 24 | $0.0082 |
   | `groq:llama-3.3-70b-versatile` | 3 | 24 | $0.0220 |
   | `anthropic:claude-3-5-haiku-20241022` | 3 | 24 | $0.0790 |
   | `openai:gpt-4o-2024-11-20` | 3 | 24 | $0.2050 |

   So a two-model, three-repetition study is a few cents on the cheap models. Scale up only
   after reviewing the pilot.
3. After a live run exists: replace `FAILURE_ANALYSIS.md` §0–§4 with real entries using the
   §2 format, update README §6/§7 with the real table, and switch the video narration to
   Variant B.
4. Record the walkthrough, publish it, paste the same URL into README §2 and HackerRank Q2.
5. Rebuild and re-verify the archive: `python scripts/build_submission_zip.py`.
6. Accept the Participant Agreement yourself and perform the final submit. (Not done by the
   agent, by instruction.)

**Not blocked — can be improved now:** more tasks (keep 5–10), a second retriever design,
per-task sensitivity analysis, or an LLM-judge track *with* a measured agreement study.
