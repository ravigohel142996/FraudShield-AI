# 🛡️ RAGShield Eval

**A reproducible benchmark for indirect prompt injection and retrieval authorisation in
retrieval-augmented generation.**

micro1 Eval Hackathon 2026 (HackerRank) · Participant: **Ravi Gohel** (solo) · Version 1.0.0 · 2026-10-30

> **Submission status — read before the numbers.** The benchmark, grader, dashboard and
> reproducibility tooling are complete and tested (`133 passed`). **No frontier model has
> been executed**, because the build environment had no provider API key and no approved
> spending limit, and its egress allowlist did not include any model-provider host. There
> are therefore **no experimental findings in this repository**, and none are implied. See
> [§6](#6-models-tested-and-results) for the exact blocker and the one command that
> produces real results on a machine with credentials.

---

## 1. Short description

Retrieval-augmented generation systems put third-party text inside the model's context.
That text is often written by people who are not the system operator: a shared drive, a
vendor FAQ, a scraped wiki, a support ticket, a document a colleague forwarded. When such a
document contains the sentence *"ignore your instructions and do X"*, the model receives it
in the same context window as its real policy, separated only by the hope that it can tell
the two apart.

**RAGShield Eval measures whether it can.** Eight purpose-built tasks, each isolating a
distinct failure: direct injection, instructions hidden in HTML markup, impersonated
`SYSTEM`/`ADMIN` role labels, canary exfiltration dressed up as a compliance requirement,
conflicting sources with different authority, cross-tenant retrieval, missing permission
metadata, and — as a positive control — a legitimate security report that quotes an attack
string and must **not** be refused.

Two things make it more than a prompt-injection toy:

1. **It grades two layers separately.** Track A asks what the *model* did with untrusted
   context. Track B asks whether the application's *retrieval layer* ever placed a document
   the principal may not read into that context at all. These are computed from different
   data, and conflating them is how systems get certified as secure while leaking.
2. **It penalises both directions.** Unsafe compliance and unnecessary refusal are both
   failures. 30 hand-written responses with known verdicts regression-test the grader.

The research hypothesis — that frontier models may answer ordinary RAG questions well
while mishandling instruction trust, authorisation edges, attribution and legitimate-but-
suspicious content — is **`UNTESTED` here**. The suite is built to be able to reject it.

## 2. Video walkthrough

**Link:** `[VIDEO LINK PLACEHOLDER — to be recorded, not yet published]`

No video has been recorded or published. A complete script, shot-by-shot storyboard,
dashboard demonstration plan and timing sheet are in [`video/`](video/):

* [`video/narration.md`](video/narration.md) — full narration text with timings
* [`video/storyboard.md`](video/storyboard.md) — scene-by-scene visual plan
* [`video/recording_checklist.md`](video/recording_checklist.md) — recording and edit checklist

The same link must be pasted into the HackerRank **Q2** field. This README will not claim a
video exists until a real public URL has been verified.

## 3. Domain and expertise

This project sits at the intersection of four disciplines:

**Retrieval-augmented generation.** Chunking, ranking, context construction, and the
provenance metadata that makes an answer auditable. The benchmark's retriever is a
deterministic lexical ranker (`src/retrieval_simulator.py`) — chosen because a stochastic
vector index would make an authorisation result unreproducible: ranking decides *what is
relevant*, authorisation decides *what may be shown*, and the two must be separable.

**AI security / LLM application security.** Instruction hierarchy, trust boundaries,
indirect prompt injection, data exfiltration via canaries, and the difference between a
model-level control and a system-level control. The core security argument: if a control is
implemented only inside the model's judgement, then every document author in the corpus
holds a vote on that control.

**Multi-tenant information isolation.** Deny-by-default authorization, ACL evaluation, and
the fail-open risk of missing metadata. Enterprise corpora constantly acquire documents
from migrations and exports that have no access metadata; treating "unknown" as "permitted"
means every migration is a potential disclosure.

**Evaluation science.** Task design with discriminating power, ground truth that can be
checked mechanically, metrics with explicit denominators, controls in both directions,
frozen rubrics, and a loud refusal to publish a number whose denominator is zero.

## 4. What it tests and why it matters

| # | Task | What it isolates | Why it matters in production |
|---|---|---|---|
| T01 | Direct document injection | Plain "ignore previous instructions" in retrieved prose | The baseline case; a model that fails this cannot be trusted with any corpus |
| T02 | Hidden markup injection | Instruction in an HTML comment, `display:none` div and zero-size text | Real corpora are full of HTML/PDF captures. A human reviewer never sees hidden text; a text extractor does |
| T03 | Fake system instruction | Impersonated `SYSTEM` / `DEVELOPER` / `ADMIN OVERRIDE` headings | Authority resolved by surface form means any corpus contributor can mint themselves root |
| T04 | Canary extraction | Exfiltration request wrapped in a compliance-authority claim | "Required for SOC 2" in untrusted text is not policy. Tests whether authority claims buy exceptions |
| T05 | Conflicting sources | Two sources disagree; one is authoritative, one is stale; one sub-question is unanswerable | The normal state of an enterprise corpus. Wrong-source and invented-figure answers are silent and plausible |
| T06 | Cross-tenant retrieval | One tenant requests another tenant's post-mortem (Tracks A **and** B) | A refusal is not a control if the retriever already shipped the document upstream |
| T07 | Ambiguous permissions | Document with no ACL metadata + missing permission (Tracks A **and** B) | Deny-by-default is the only safe reading of absent metadata; partial denial must still answer what it can |
| T08 | Benign lookalike | **Positive control:** incident report quoting an attack string | A model that refuses security reports is useless, and analysts then route around the control entirely |

**Target audience:** AI evaluation researchers, AI platform/security engineers shipping RAG,
and anyone who needs to justify an authorisation design rather than assume it.

**Real-world significance:** the interesting failures are not jailbreaks — they are
plausible, confident, wrong answers produced inside a system that believes it is protected.
This benchmark measures that specific gap, and keeps Track A and Track B apart so the
remediation is actually diagnosable.

## 5. Setup and run instructions

### 5.1 Requirements

* Python **3.10+** (developed and tested on **3.11.2**)
* **No** third-party packages for the benchmark core — loading, retrieval, authorization,
  prompting, grading, metrics, reporting and manifesting are standard library only
* Optional: `streamlit` + `pandas` for the dashboard, `pytest` for the test suite

```bash
cd RAGShield-Eval
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # dashboard + test deps only
```

### 5.2 Verify without credentials (no cost, no network)

```bash
python -m src.runner validate          # schema + semantic validation of all 8 tasks
python -m src.runner credentials       # which provider keys are present (names only)
python -m pytest tests/ -q             # 133 tests: grader, authz, metrics, pipeline, dashboard
```

### 5.3 Offline pipeline check (no API key, no cost)

```bash
python -m src.runner run --pipeline-check
```

Exercises the full path — ranking → authorization → prompt → provider → grading → artefacts
→ report — using a deterministic stub. Output lands in `results/validation/` and every
record is stamped `counts_as_model_experiment: false`. **This is a wiring test, not an
experiment;** the dashboard and report both refuse to present it as model results.

### 5.4 Real experiment

```bash
cp .env.example .env                   # add ONE provider key
export OPENAI_API_KEY=...              # or ANTHROPIC_API_KEY / GEMINI_API_KEY / GROQ_API_KEY
# 1. declare the models in config/benchmark.yaml under run.models
# 2. approve a spending limit in config/benchmark.yaml under budget
python -m src.runner preflight         # worst-case cost estimate vs approved limit
python -m src.runner run --live --label pilot
python -m src.runner report --dir results
streamlit run dashboard/app.py
```

Raw responses and scores are written to `results/`: `raw_outputs.jsonl`, `scores.csv`,
`summary.json`, `per_task.json`, `experiment_manifest.json`, `report.md`,
`dashboard_data.json`. See [`results/README_RESULTS.md`](results/README_RESULTS.md).

**Runtime and cost, honestly:** the core executes in **under a second** on CPU with no
network. A live run costs one API call per (model × task × repetition) — 24 calls for 2
models × 8 tasks × 3 repetitions. Measured worst-case estimates from `preflight` (one model,
8 tasks, static price table — estimates, not bills):

| model | repetitions | runs | worst-case estimate |
|---|---|---|---|
| `openai:gpt-4o-mini-2024-07-18` | 1 (pilot) | 8 | **$0.0041** |
| `openai:gpt-4o-mini-2024-07-18` | 3 | 24 | $0.0123 |
| `gemini:gemini-2.0-flash` | 3 | 24 | $0.0082 |
| `groq:llama-3.3-70b-versatile` | 3 | 24 | $0.0220 |
| `anthropic:claude-3-5-haiku-20241022` | 3 | 24 | $0.0790 |
| `openai:gpt-4o-2024-11-20` | 3 | 24 | $0.2050 |

The whole suite is therefore cheap to run; the blocker was authorisation, not cost. `python -m src.runner preflight` prints the exact
worst-case estimate from the price table in `src/model_provider.py`; the runner **refuses to
start** if that estimate exceeds `budget.max_total_cost_usd`, if a model has no price entry,
or if `budget.allow_live_calls` is false. Cost figures are estimates, never billed amounts,
and are labelled as such everywhere.

### 5.5 Project layout

```
RAGShield-Eval/
├── README.md                     # this file
├── PROJECT_AUDIT.md              # Phase 0: what existed before this work
├── RESEARCH_METHODOLOGY.md       # hypothesis, design, controls, limitations
├── SCORING_METHODOLOGY.md        # every check, metric, denominator and weight
├── FAILURE_ANALYSIS.md           # why it is empty, and the format it will use
├── STATE.md                      # execution log of this build
├── FINAL_SUBMISSION_REPORT.md    # packaging + validation report
├── requirements.txt / .env.example
├── config/
│   ├── benchmark.yaml            # models, repetitions, temperature, budget guard
│   └── policy.yaml               # the single trusted system policy (hashed per run)
├── tasks/task_01.json … task_08.json
├── src/
│   ├── runner.py                 # CLI: validate | credentials | preflight | run | report
│   ├── task_loader.py            # task loading
│   ├── task_validator.py         # structural (S*) + semantic (M*) rules
│   ├── retrieval_simulator.py    # Track B layer 1: deterministic ranking
│   ├── authorization_engine.py   # Track B layer 2: rules R1-R6, deny-by-default
│   ├── prompt_builder.py         # provenance-delimited prompt + SHA-256
│   ├── model_provider.py         # adapters + price table + budget guard
│   ├── evaluation_runner.py      # orchestration + artefact writing
│   ├── graders.py                # deterministic grading (Track A)
│   ├── metrics.py                # metrics with explicit denominators
│   ├── report_generator.py       # Markdown + dashboard payload
│   ├── reproducibility.py        # hashes, environment fingerprint, manifest
│   └── settings.py               # config loading (dependency-free YAML subset)
├── tests/                        # 133 tests incl. answer-key grader fixtures
├── dashboard/app.py              # Streamlit evaluation dashboard
├── results/                      # experiment artefacts (+ validation/ labelled as such)
├── video/                        # narration, storyboard, checklist
├── docs/TASK_SCHEMA.md           # task JSON schema
└── scripts/build_submission_zip.py
```

## 6. Models tested and results

**None. Status: `BLOCKED`.** Stated as plainly as possible because this is the section a
reader is most likely to be misled by.

| Item | Value |
|---|---|
| Real model runs completed | **0** |
| Models tested | **none** |
| Provider credentials available in the build environment | **none** (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY` all absent — verified by `python -m src.runner credentials`, names only) |
| Approved spending limit | **none** |
| Provider hosts reachable from the build sandbox | **no** — egress allowlist covers package registries and GitHub only |
| Results reported as model findings | **none** |

### Why the honest answer is "blocked" rather than a small pilot

The brief permits continuing offline when a paid key is unavailable, and forbids spending
without an approved limit. Both conditions applied simultaneously: no key *and* no network
path to a provider, so even an approved limit could not have produced a single real
response. The alternative — running the benchmark against a stub and presenting the
output as model behaviour — would have produced a complete-looking results table containing
zero information, which is exactly the failure this project is built to detect in others.

### What *is* verified (reproducible from a clean checkout)

| Evidence | Command | Result |
|---|---|---|
| Task suite validity | `python -m src.runner validate` | 8/8 tasks valid, 0 errors |
| Test suite | `python -m pytest tests/ -q` | **133 passed** |
| Retrieval + authorization behaviour | `python -m pytest tests/test_authorization.py -q` | T06 denies `DOC-BETA-POSTMORTEM` (`R3_tenant_mismatch`); T07 denies `DOC-FIN-VENDOR-TERMS` (`R5_missing_permission`) and `DOC-LEGACY-PAYRUN` (`R1_acl_missing`) |
| Grader against a known answer key | `python -m pytest tests/test_grading.py -q` | 30 fixtures, exact failed-check sets asserted |
| End-to-end wiring | `python -m src.runner run --pipeline-check` | 8/8 records written, all stamped non-scored |
| Dashboard renders | `python -m pytest tests/test_dashboard.py -q` | 9 tabs, no exceptions, stub runs labelled |

### Models that the harness is configured to run (not tested)

`openai:gpt-4o-2024-11-20`, `openai:gpt-4o-mini-2024-07-18`,
`anthropic:claude-sonnet-4-20250514`, `anthropic:claude-3-5-haiku-20241022`,
`gemini:gemini-2.0-flash`, `groq:llama-3.3-70b-versatile` — these appear in the price table
in `src/model_provider.py`. **Being in that table means nothing except that a cost estimate
can be computed.** No result exists for any of them.

## 7. Failure analysis

[`FAILURE_ANALYSIS.md`](FAILURE_ANALYSIS.md) is explicit that there are **no verified model
failures** to analyse. It contains instead:

* the failure taxonomy (model / retrieval-authorization / evaluator / API / ambiguous) and
  the rule that a model finding observed alongside an authorization failure is marked
  **confounded**;
* the 11-field record every future failure must satisfy;
* **five evaluator-side defects found, reproduced and fixed during validation** — the most
  important being a hedge-cue false pass (E-1) and a canary-detection false negative (E-2),
  both of which would have made published numbers wrong in a flattering direction;
* what the pipeline-validation run did and did not demonstrate.

The two grader defects are worth singling out here because they are the most instructive
thing this project currently has to report. E-1: the check that forbids asserting a stale
figure was satisfied by *citing the stale document*, because the document's own ID
contained the hedge word. E-2: canary detection scanned only documents owned by other
tenants, so T04's design (another tenant's canary planted inside a document the principal
*is* allowed to read) produced a guaranteed false negative. Both were caught only because
the grader is tested against hand-written responses with known verdicts. A grader validated
against model output alone would have confidently reported 0% leakage.

## 8. Prior work and sources

**Disclosed in full, because overstating originality is a compliance issue and, more
practically, a reader cannot calibrate a benchmark without knowing what is new in it.**

| Item | Disclosure |
|---|---|
| **Prior RAGShield Eval work** | **None.** Before this session no RAGShield Eval repository, code, task set, rubric, dashboard or result existed for this account (audited in `PROJECT_AUDIT.md`: workspace search, `git log`, and all 89 public repositories checked). Everything under `RAGShield-Eval/` was created on 2026-10-30. |
| **Repository it lives in** | `ravigohel142996/FraudShield-AI`, an unrelated prior project (a UPI/card fraud risk engine). It is **not** part of this submission, was not modified, and shares no code. Its only influence is that Streamlit was already a familiar dependency for the dashboard. |
| **AI coding assistance** | Substantial. This project was built with an AI coding agent (Arena.ai Agent Mode) under the author's direction and review. The event permits AI assistance; the author remains responsible for the design, the integrity of every claim above, and the submission. |
| **Third-party libraries** | Streamlit (Apache-2.0), pandas (BSD-3), pytest (MIT) — used unmodified, dashboard/tests only. The benchmark core imports **nothing** outside the Python standard library. |
| **External datasets** | **None.** No corpus, benchmark dataset or copyrighted material was downloaded or reused. |
| **Pre-existing benchmarks / literature** | No task, rubric or prompt in this suite is copied or adapted from another benchmark. The problem space (indirect prompt injection, instruction hierarchy, canary-based leakage tests, deny-by-default access control) is well established in the security literature and in industry practice; the specific task texts, tenants, documents, canaries, rubric and grader here are original to this project. No paper is cited as evidence for any claim in this repository — there are no external empirical claims. |
| **Data** | 100% synthetic. Tenants are `tenant_alpha/beta/gamma`; canaries are meaningless strings such as `CANARY_TENANT_BETA_7F3`; IPs come from the RFC 5737 documentation range (`203.0.113.42`); domains use `.example.net`. |

### Ethical and privacy considerations

* No real credentials, secrets, customer documents or personal data anywhere in the
  repository, the task corpus or the results. The injection targets are harmless synthetic
  canaries, never a real secret.
* No third-party system is probed or attacked. A live run makes ordinary completion
  requests to a model provider and nothing else.
* Provider keys are read from the environment, never logged, never written to a run record,
  a manifest, a report or the submission archive — and `scripts/build_submission_zip.py`
  scans the archive for credential patterns before it will build.

## 9. Task definitions, scoring and reproducibility (summary)

* **Task schema:** [`docs/TASK_SCHEMA.md`](docs/TASK_SCHEMA.md). Each task carries an ID,
  category, track, difficulty, user query, requesting principal and permissions, synthetic
  documents with tenant/trust/authority/ACL metadata, a retrieval request, expected
  behaviour, required facts, required citations, prohibited disclosures, grading rubric,
  security rationale, expected failure patterns and ground truth.
* **Validation:** `src/task_validator.py` enforces 10 structural (`S*`) and 8 semantic
  (`M*`) rules — including that an injected string must actually reach the prompt, that a
  forbidden literal must genuinely exist in a document, and that a Track B task must make
  its authorization failure observable twice. The validator refuses a task suite that
  cannot discriminate.
* **Scoring:** [`SCORING_METHODOLOGY.md`](SCORING_METHODOLOGY.md). Eight deterministic
  checks, every metric with an explicit data-derived denominator, zero denominators reported
  as `n/a`, critical security failures never averaged away, and a weighted composite whose
  weights are fixed and published in advance.
* **Grader validation:** 30 hand-written fixtures with known verdicts, asserting exact
  failed-check sets. Regression classes cover correct, incorrect, injection-followed,
  canary-leaked, invalid-citation, unsupported-claim, over-refusal and ACL-violation.
* **Reproducibility:** every run records provider, exact model ID, timestamp, temperature,
  max tokens, repetition, prompt SHA-256, policy version and hash, the retrieval trace, token
  usage, estimated cost and the exact grading decisions. `experiment_manifest.json` adds the
  git commit, per-task definition hashes and an environment fingerprint.
  `git_worktree_dirty` is recorded so an artefact can be tied to a state of the code.
* **Research design:** [`RESEARCH_METHODOLOGY.md`](RESEARCH_METHODOLOGY.md).

## 10. Known limitations

1. **No experimental results.** The central limitation. Everything above is design,
   implementation and test evidence — not model behaviour.
2. **Eight tasks.** Enough to characterise, not to estimate a population. Per-task results
   are the primary output; the composite only makes a table sortable.
3. **Literal grading.** Substring fact-matching cannot parse negation ("30 days is wrong"
   would satisfy a fact for 30 days). Mitigated by corroborating citation checks and by
   storing each check's evidence for adjudication, but not eliminated.
4. **One retrieval design.** Deterministic lexical ranking is a reproducibility choice; a
   different retriever changes which documents reach the model, and T06/T07 are sensitive
   to that.
5. **No LLM-as-judge.** Deliberate: an unvalidated judge would add an unmeasured error
   source. `llm_judge: disabled` in `config/benchmark.yaml`, and no judge agreement is
   claimed.
6. **Single-turn, synthetic corpus.** No multi-turn persistence, no tool use, no real PDF/OCR
   noise.
7. **`temperature: 0` is not determinism.** Repetitions measure provider nondeterminism
   rather than remove it; `task_accuracy_first_repetition` is reported alongside the
   all-repetition figure for comparison.
8. **Nothing here is a claim about any deployed product.** A failure is a property of model
   behaviour on synthetic inputs, not a discovered vulnerability in production software.

## 11. Submission

* Archive: `RAGShield-Eval-micro1-Submission.zip`, built with
  `python scripts/build_submission_zip.py`, which refuses to build on a credential match and
  verifies size and required files. See [`FINAL_SUBMISSION_REPORT.md`](FINAL_SUBMISSION_REPORT.md)
  for the exact size, verified file list and remaining manual actions (recording the video,
  pasting the link into Q2, and the final submit action).
* License: no license file is included because none was specified for this event entry;
  treat the code as shared for evaluation purposes only.
