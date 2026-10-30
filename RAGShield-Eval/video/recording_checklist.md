# Recording checklist

## A. Before recording — technical

- [ ] Clean checkout runs: `python -m src.runner validate` → 8/8 valid
- [ ] `python -m pytest tests/ -q` → `133 passed` (record the real number; if it differs,
      say the real one)
- [ ] `python -m src.runner credentials` → shows which keys are absent (and never a value)
- [ ] `python -m src.runner run --pipeline-check` → `results/validation/` regenerated
- [ ] `streamlit run dashboard/app.py` → dashboard loads, all 9 tabs render without error
- [ ] Dashboard run selector shows the validation run with its **stub** label
- [ ] Terminal font ≥ 16pt; browser zoom 110%; dark theme
- [ ] `.env` not open in any editor tab; no key visible in shell history on screen
- [ ] Screen resolution 1920×1080; microphone tested; 30 s test clip reviewed

## B. Before recording — integrity

- [ ] Decide which narration variant you are recording (A = no live run, B = live run exists)
- [ ] If Variant A: the red "PIPELINE VALIDATION — NOT MODEL RESULTS" banner is in shot
- [ ] If Variant B: `results/<run>/summary.json` has `counts_as_model_experiment: true`, and
      every number in the script was copied from that file, not from memory
- [ ] If Variant B: write down the exact model IDs and repetition count you will say aloud
- [ ] No sentence in the script claims a vulnerability in a real production system
- [ ] No sentence claims an LLM judge was validated (it is disabled)

## C. During recording

- [ ] Speak the model IDs exactly as they appear in the artefact (`gpt-4o-mini-2024-07-18`,
      not "GPT-4o mini")
- [ ] Pause 1 s between scenes for clean cuts
- [ ] Hold any table or banner you reference for ≥ 2 s
- [ ] Do not narrate over a scroll; land, then speak
- [ ] If you misstate a number, stop and re-take that scene — do not "fix it in post"

## D. After recording

- [ ] Trim to ≤ 5:00 (target 4:40)
- [ ] Burn in captions; verify no key/secrets in any frame at 1× speed
- [ ] Audio: normalise to roughly −16 LUFS, remove clipping
- [ ] Export 1080p, H.264, ≤ 500 MB
- [ ] Upload (unlisted or public)
- [ ] Verify in a private/incognito window that the link plays without sign-in
- [ ] Paste the identical URL into `README.md` §2 and HackerRank **Q2**
- [ ] Delete the local raw recording from any folder that will be zipped

## E. Never do

- Never state a metric that is not visible in an artefact file in this repository.
- Never describe the stub run as a model experiment, pilot, or smoke test of behaviour.
- Never claim the video is public before verifying it in a private window.
- Never upload anything to a public destination without the participant's explicit approval.
