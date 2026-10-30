# Storyboard — RAGShield Eval walkthrough (≤ 5:00)

Screen resolution 1920×1080, browser zoom 110%, dark terminal theme, no personal tabs,
notifications off. Two recording sources: **terminal** and **dashboard**. No face cam needed.

| # | Time | Visual | Action on screen | Audio (narration §) | On-screen caption |
|---|---|---|---|---|---|
| 1 | 0:00–0:08 | Title card | Static: project name, "micro1 Eval Hackathon 2026", author, date | — | RAGShield Eval |
| 2 | 0:08–0:35 | Terminal | `python -m src.runner credentials` → shows all four keys absent | Scene 1 | "The model is not an authorisation control" |
| 3 | 0:35–1:00 | Diagram (static PNG or Markdown render) | Left: system policy. Right: retrieved doc containing an injected instruction. Arrow labelled "same context window" | Scene 2 | hypothesis framed as a hypothesis |
| 4 | 1:00–1:20 | Dashboard → Overview | Scroll the KPI row; stop on "Models tested" | Scene 3 part 1 | **Track A:** model behaviour · **Track B:** retrieval authority |
| 5 | 1:20–1:45 | Dashboard → Retrieval authorisation | Highlight denied rows + rule IDs; then the "Invariant holds" line | Scene 3 part 2 | "A refusal is not a control if the document already shipped" |
| 6 | 1:45–2:05 | Dashboard → Tasks | Filter Track = A; scroll the table | Scene 4 part 1 | 8 tasks · 8 distinct phenomena |
| 7 | 2:05–2:20 | Dashboard → Tasks → T02 opened | Expand `DOC-HELPDESK-MIRROR-7`; the HTML comment and `display:none` are visible in the code block | Scene 4 part 2 | "Invisible to a reviewer, visible to a text extractor" |
| 8 | 2:20–2:30 | Dashboard → Tasks → T08 opened | Show the quoted attack string inside the incident report | Scene 4 part 3 | Positive control: refusing this is a failure |
| 9 | 2:30–3:05 | Dashboard → Scoring | Point at `numerator/denominator` column; then the critical-failure line | Scene 5 | "Zero denominator ⇒ n/a. Critical failures are never averaged away." |
| 10 | 3:05–3:25 | Editor: `tests/fixtures/grader_fixtures.py` | Scroll `T05-stale-figure-asserted` and `T04-canary-leak` | Scene 6 part 1 | 30 hand-written answer-key responses |
| 11 | 3:25–3:40 | Terminal | `pytest tests/ -q` → `133 passed` | Scene 6 part 2 | Two real grader defects caught and fixed |
| 12 | 3:40–4:05 | Terminal | `runner validate` (8/8 valid) → `pytest` → `run --pipeline-check` | Scene 7 (Variant A) | Verified: schema, rules, tests, wiring |
| 13 | 4:05–4:20 | Dashboard → Overview | Hold on the **red** banner: "PIPELINE VALIDATION — NOT MODEL RESULTS" | Scene 7 (Variant A) | **No model results — and none fabricated** |
| 13B | 4:05–4:20 | Dashboard → Overview (**Variant B only**) | Hold on the **green** badge "REAL MODEL EXPERIMENT", then the metrics table | Scene 7 (Variant B) | Real run: `<models>` · `<runs>` · `<cost estimate>` |
| 14 | 4:20–4:35 | Dashboard → Reproducibility | Pan across git commit, policy hash, per-task hashes; open the JSON manifest | Scene 8 part 1 | Re-derivable from the stored artefact |
| 15 | 4:35–4:50 | Dashboard → Export | Click one download button to show the artefacts are real files | Scene 8 part 2 | One command. Standard library core. |
| 16 | 4:50–5:00 | Title card | Same as scene 1, plus "no fabricated results" line | Scene 8 close | RAGShield Eval |

## Screens to prepare before pressing record

1. `results/validation/` present so the dashboard has a run to show (already generated).
2. Terminal scrollback cleared; font ≥ 16pt so code is legible at 1080p.
3. `tests/fixtures/grader_fixtures.py` open at the T05 fixture line.
4. Dashboard on the **Overview** tab and pre-warmed (Streamlit's first render is slow).
5. Browser bookmarks bar hidden.

## Shot list (in recording order)

| Shot | Source | Length | Notes |
|---|---|---|---|
| S1 | Title card | 8 s | Can be a still with a slow fade |
| S2 | Terminal | 27 s | `credentials` output must be visible; no keys in it by design |
| S3 | Diagram | 25 s | Build as a simple two-column graphic; avoid stock imagery |
| S4–S5 | Dashboard | 45 s | One continuous take is fine; cut out mouse hunting |
| S6–S8 | Dashboard | 45 s | Slow scrolls; hold ≥2 s on each task you name |
| S9 | Dashboard | 35 s | Do not let the mouse cover the denominator column |
| S10–S11 | Editor + terminal | 35 s | The fixtures must be legible; zoom the editor |
| S12–S13 | Terminal + dashboard | 40 s | The red banner must be on screen for ≥10 s |
| S14–S15 | Dashboard | 30 s | Show a real file download |
| S16 | Title card | 10 s | End card |

## Editing checklist

- [ ] Runtime ≤ 5:00 (hard cap; aim for 4:40)
- [ ] No API key, token or `.env` content visible in any frame
- [ ] No personal data, tabs, notifications or unrelated windows
- [ ] Every number spoken appears on screen from a real artefact file
- [ ] Red banner shown clearly in Variant A / green badge in Variant B
- [ ] Captions burned in or uploaded (accessibility)
- [ ] Audio normalised, no clipping, no room echo
- [ ] Upload unlisted-or-public, then verify the link in a private window
- [ ] Paste the same URL into `README.md` §2 and HackerRank Q2
