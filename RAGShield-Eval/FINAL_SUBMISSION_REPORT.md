# FINAL_SUBMISSION_REPORT.md

**Project:** RAGShield Eval · **Participant:** Ravi Gohel (solo) · **Event:** micro1 Eval Hackathon 2026 (HackerRank)
**Report date:** 2026-10-30 · **Deadline:** 2026-11-09 10:45 IST

---

## 1. Final project status

**Technically complete and reproducible; experimentally unexecuted.**

| Area | Status |
|---|---|
| Benchmark suite (8 tasks, 8 categories, 2 tracks) | ✅ complete, validator-clean |
| Grading (8 deterministic checks) + metrics with explicit denominators | ✅ complete |
| Track B authorization engine (rules R1–R6) | ✅ complete, tested per rule |
| Model providers (OpenAI, Anthropic, Gemini, Groq) + budget guard | ✅ complete, **never called with a real key** |
| Runner, artefacts, manifests, reports | ✅ complete, pipeline validated offline |
| Dashboard (9 sections) | ✅ complete, renders without exceptions |
| Documentation set (README + 5 analysis docs + schema + video pack) | ✅ complete |
| Submission archive | ✅ built, 53 files, 0.14 MB, clean-env verified |
| **Real model experiments** | ❌ **BLOCKED** — see §9 |
| **Video** | ❌ **not recorded** — script ready, see §12 |
| Participant Agreement | ⚠️ **not accepted** — participant action, by instruction |

This is an honest "not ready to submit *as a result-bearing study*" status rather than a
false green tick. Everything required *except* real model runs and the video exists and has
been executed and verified.

## 2. Research hypothesis

> Frontier AI models may answer normal RAG questions correctly but fail to consistently
> distinguish trusted system instructions from untrusted instructions embedded in retrieved
> documents. They may also mishandle authorization boundaries, source attribution, and
> suspicious-looking but legitimate content.

**Status: `UNTESTED`.** No model has been run, so the hypothesis is neither supported nor
rejected. The suite is designed so that a model passing all eight tasks would *reject* it.

## 3. Verified experimental findings

**None.** There are zero model responses in this repository.

What *is* verified (`VERIFIED`, reproducible by the test suite):

1. All 8 tasks are structurally and semantically valid, including that every injected string
   actually reaches the model's context and every forbidden literal genuinely exists in a
   document.
2. The authorization engine denies exactly the right documents for the right reasons:
   T06 excludes `DOC-BETA-POSTMORTEM` (`R3_tenant_mismatch`); T07 excludes
   `DOC-FIN-VENDOR-TERMS` (`R5_missing_permission`) and `DOC-LEGACY-PAYRUN` (`R1_acl_missing`).
3. The Track B invariant holds for every task: no denied document ever appears in
   `prompt_doc_ids`.
4. The grader returns the expected verdict for 30 hand-written responses with known answers.
5. The full pipeline runs end-to-end and writes every artefact, with stub output excluded from
   all metrics by construction.
6. Two real grader defects were found and fixed (see §7 and `FAILURE_ANALYSIS.md` §3).

## 4. Models tested

**None.**

| Provider | Credential | Status in build environment |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | not set |
| Anthropic | `ANTHROPIC_API_KEY` | not set |
| Gemini | `GEMINI_API_KEY` | not set |
| Groq | `GROQ_API_KEY` | not set |

Six model IDs appear in the price table (`src/model_provider.py`) purely so that cost
estimates can be computed. **Being listed there is not evidence of a test.**

## 5. Real completed runs

**0 scored runs. 0 API calls.** Total: **0**.

The 8 records in `results/validation/raw_outputs.jsonl` are a deterministic stub pipeline
check, stamped `provider_class: pipeline_validation_stub` and `counts_as_scored: false` on
every row. They are excluded from every metric and are labelled "NOT MODEL RESULTS" in the
dashboard and report.

## 6. Individual metric scores

**None can be reported.** Every metric's denominator is zero for a real model, and
`src/metrics.py` returns `null` / `not_applicable` rather than a flattering default. The
metrics that *would* be reported, with their denominators, are defined in
`SCORING_METHODOLOGY.md` §4:

`task_accuracy` · `injection_resistance` · `canary_leakage_rate` · `unauthorized_retrieval_rate`
· `citation_correctness` · `grounding_correctness` · `false_refusal_rate` ·
`appropriate_abstention_rate` · `critical_security_failures` (reported separately, never
averaged).

## 7. Scoring reliability evidence

| Evidence | Result |
|---|---|
| Answer-key fixtures (hand-written, not model output) | **30**, each asserting the **exact** set of failed checks |
| Regression classes covered | correct · incorrect · injection-followed · canary-leaked · invalid citation · unsupported claim · over-refusal · ACL violation |
| Determinism | `test_grading_is_deterministic` — identical output on repeat |
| Zero-denominator policy | `test_zero_denominator_reports_not_applicable_not_perfect_score` |
| Critical failures not averaged away | `test_critical_security_failures_are_counted_not_averaged_away` |
| Grader defects found by the suite | **2** (hedge-cue false pass; canary false negative) — both fixed and pinned |
| LLM-as-judge | **disabled**; no judge agreement is claimed because none was measured |

## 8. Test results (actual output)

```
$ python -m src.runner validate
Loaded 8 tasks from tasks/
  T01  easy   A    direct_document_injection  — Direct document injection
  T02  medium A    hidden_markup_injection  — Hidden markup injection
  T03  medium A    fake_system_instruction  — Fake system / developer / admin instruction
  T04  hard   A    canary_extraction  — Synthetic canary extraction
  T05  hard   A    conflicting_sources  — Conflicting retrieved sources with different authority
  T06  hard   A/B  cross_tenant_retrieval  — Cross-tenant retrieval request
  T07  hard   A/B  ambiguous_permissions  — Missing or ambiguous permission metadata
  T08  medium A    benign_lookalike  — Benign lookalike content (positive control)
All tasks valid.

$ python -m pytest tests/ -q
133 passed in 0.96s
```

Clean-environment verification (extracted archive, fresh venv, `pip install -r requirements.txt`):

```
unzip -q RAGShield-Eval-micro1-Submission.zip -d /tmp/ragshield-clean   # 53 files
python3 -m venv /tmp/ragshield-clean-venv
pip install -r requirements.txt                                        # streamlit, pandas, pytest
python -m src.runner validate            -> All tasks valid.
python -m src.runner credentials         -> 4/4 provider keys absent
python -m src.runner run --pipeline-check-> 8 records written
python -m pytest tests/ -q               -> 133 passed in 0.96s
```

Standard-library-only check (`/usr/bin/python3`, no third-party packages installed):
`validate` OK; `run --pipeline-check` OK; direct import chain loader→retrieval→prompt→grader
OK (`task_passed=True` for a known-good T06 response).

## 9. Known blockers

| Blocker | Evidence | Consequence |
|---|---|---|
| No provider credential in the build environment | `python -m src.runner credentials` → 4/4 "is not set" | cannot call a model |
| No approved spending limit | integrity rule J; no approval was given | must not call a paid model even if a key existed |
| Provider hosts unreachable from the sandbox | egress allowlist covers package registries + GitHub only | a key alone would not fix it here |
| Video not recorded | requires the participant's voice/screen | Q2 field cannot be completed |

**Not a blocker:** cost. Worst-case estimates are cents — `gpt-4o-mini` × 8 tasks × 3
repetitions ≈ **$0.0123**; the cheapest full study is ≈ $0.008. The blocker is authorisation,
not budget.

## 10. Archive

| Item | Value |
|---|---|
| Path | `RAGShield-Eval/RAGShield-Eval-micro1-Submission.zip` |
| Size | **143,434 bytes (0.14 MB)** — limit 50 MB |
| Members | **53** |
| `README.md` at archive root | ✅ verified |
| Required documentation present | ✅ 15 required paths + 8 task files checked individually |
| Credential scan (7 patterns, pre-build gate) | ✅ clean — build aborts on any hit |
| Live `.env` / `.venv` / `.git` / caches / videos / nested archives | ✅ excluded |
| Clean-env extract + install + test | ✅ 133 passed |

Builder: `python scripts/build_submission_zip.py` (rebuilds and re-verifies; exit 0 = pass).
Note: the archive root **is** the project root, so `README.md` sits at the top level as
required, rather than nested inside a wrapper folder.

## 11. README

`RAGShield-Eval/README.md` — contains all required sections: short description, video link
(placeholder), domain and expertise, what it tests and why it matters, setup/run
instructions with runtime and cost, models tested and results (explicitly "none, blocked"),
failure analysis, prior work and sources (full disclosure), task definitions, scoring
methodology, grader validation, experiment methodology, ethics/privacy, known limitations,
and submission details.

## 12. Video readiness

| Item | Status |
|---|---|
| Narration script | ✅ `video/narration.md` — 8 scenes, 4:40 target, two variants (A: no live run; B: after a live run) |
| Storyboard | ✅ `video/storyboard.md` — 16 numbered shots with timings and on-screen captions |
| Recording checklist | ✅ `video/recording_checklist.md` |
| Recorded | ❌ |
| Public URL | ❌ **none** — no link is claimed anywhere; README §2 shows a marked placeholder |
| Rendering tool available | ❌ no video tooling in this sandbox; the participant must record |

## 13. Exact description for the HackerRank Q1 field

> RAGShield Eval is a reproducible benchmark for the trust boundary in retrieval-augmented
> generation: can a model tell its real instructions from instructions written by whoever
> authored a retrieved document?
>
> It evaluates eight hand-built scenarios — direct injection, instructions hidden in HTML
> markup, impersonated SYSTEM/ADMIN role labels, canary exfiltration dressed up as a
> compliance requirement, conflicting sources with different authority, cross-tenant
> retrieval, missing permission metadata, and a legitimate security report that quotes an
> attack string and must not be refused.
>
> Its central design choice is that it grades two layers separately. Track A measures what
> the model did with untrusted context. Track B measures, from the retrieval trace, whether
> the application ever placed a document the user may not read into that context at all — so
> a model politely refusing does not make an unsafe retriever look safe.
>
> Grading is deterministic: eight checks including canary leakage, citation validity,
> grounding, abstention and over-refusal, with explicit denominators on every metric, zero
> denominators reported as n/a, and critical security failures never averaged away. Thirty
> hand-written responses with known verdicts regression-test the grader; that answer key
> caught two real defects, including a canary check that could never have fired.
>
> Honest status: the benchmark, grader, dashboard and packaging are complete and tested (133
> passing tests, verified from a clean environment), and the retrieval/authorisation layer is
> validated per rule. No frontier model has been run yet — the build environment had no
> provider credential and no approved spending limit — so this submission claims no model
> findings rather than fabricating them. The live run is one budget-gated command.

## 14. Exact video link for Q2

**None available.** Do not submit a placeholder as a URL. Record the walkthrough using
`video/`, upload it, verify it plays in a private window, then paste that same URL into
`README.md` §2 and HackerRank Q2.

## 15. Remaining manual actions (participant)

1. **Decide project placement.** RAGShield Eval currently lives in the `FraudShield-AI`
   repository (an unrelated prior project, untouched). If it should live in its own repo, the
   `RAGShield-Eval/` directory is self-contained and moves cleanly.
2. **Approve a spending limit and supply one provider key**, then run the pilot:
   ```bash
   export OPENAI_API_KEY=...        # or ANTHROPIC_API_KEY / GEMINI_API_KEY / GROQ_API_KEY
   # config/benchmark.yaml: run.models + budget.allow_live_calls: true + max_total_cost_usd
   python -m src.runner preflight
   python -m src.runner run --live --label pilot        # 8 calls, ≈ $0.004
   ```
3. **Review the pilot** for grading sanity, then scale to 3 repetitions and a second model
   (≈ $0.02 total on the cheap models).
4. **Populate the results sections** with the real numbers: `README.md` §6/§7,
   `FAILURE_ANALYSIS.md` §0–§4, and switch `video/narration.md` to Variant B.
5. **Record, upload and verify the video**; paste the identical URL into README §2 and Q2.
6. **Review the AI-assistance disclosure** in README §8 and adjust the wording to whatever
   the event's rules require in your own voice.
7. **Rebuild the archive** after any edit: `python scripts/build_submission_zip.py`.
8. **Accept the Participant Agreement and perform the final submit yourself.** Neither has
   been done, by instruction. Submission is final after the final submit action.

---

### One-line honesty statement

Everything in this submission that claims to be verified was executed and its output is
quoted above; everything that depends on a language model is marked as not yet run, and no
number, quote or finding has been invented to fill the gap.
