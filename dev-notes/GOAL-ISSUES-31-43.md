# GOAL — Resolve All Open Issues (#31–#43) + Architecture Report

> **Project:** brandly-cli · **Created:** session goal (goal-writer skill)
> **Source issues:** GitHub `Dream-Pixels-Forge/brandly-cli` #31–#43 (all open)

## Goal: Close all 13 open issues with verified fixes

### Objective
Implement code/test/doc changes that resolve GitHub issues #31–#43, keep the full test suite passing, and close each issue with a comment.

### Context
Issues emerged from a real production run (pixels-war). They cluster into 4 areas:
- **Prompt engineering** (#31 schema, #32 scene-aware boilerplate, #38 present-chars IDENTITY_LOCK, #42 constraints/negative split)
- **Pipeline governance** (#33 storyboard gate, #34 gate threshold docs, #35 duration validation, #39 retry logging, #36 project.json sync, #37 plan naming)
- **Asset hygiene** (#40 aspect ratio, #41 reference dedup)
- **Project layout** (#43 folder restructure + `brandly migrate`)

### Deliverables
- [ ] **D1 · #42** `video_prompts.py`: `[CONSTRAINTS]` = technical limits (duration/aspect/model caps); `[NEGATIVE]` = unique visual exclusions only; no duplicated entries; section-order note in module docstring.
- [ ] **D2 · #38 + #32** `video_prompts.py`: IDENTITY_LOCK includes only characters present in the shot (presence from shot metadata `characters`/`present`, fallback: substring match of character name in shot prompt); honor `no_boilerplate: true` to skip generic `[LIGHTING]`/`[COLOR GRADE]`/`[VISUAL STYLE]` blocks when the shot specifies its own direction.
- [ ] **D3 · #31** Structured prompt schema: shot `prompt` may be a dict with 8 layers (`subject, emotion, optics, motion, lighting, style, audio, continuity`); unknown keys rejected with a clear error; string prompts keep working; dict prompts expand into the same block structure (reuses D1/D2 sections).
- [ ] **D4 · #33** New `brandly storyboard <project>` command: generate keyframe image per shot via Agnes image model, run composition check (presence/black-frame), store approved frames under `pre-production/storyboard/`, skip shots with existing approved keyframes.
- [ ] **D5 · #34** `quality_gate.py` + `brandly gate`: document threshold (in `--help` + docs), add `--threshold`, log threshold + comparison to gate report, add `--strict/--lenient` modes.
- [ ] **D6 · #35** Plan-time duration validation: warn when shot duration exceeds model max (Agnes 12s); optional `--split-long-shots` that splits shots over the max into 6s segments.
- [ ] **D7 · #36** `project.json` live sync: update `status`, `current_phase`, `shot_count` (from shots.json), reconcile `budget` with `cost.json`, append phase-transition timestamps during produce/shot runs.
- [ ] **D8 · #37** Plan filenames include shot ID: `plan_video_s01_01_YYYYMMDD-HHMMSS.md`; plan table gains a `shot_id` column; scene/act added to plan metadata.
- [ ] **D9 · #39** Retry/backoff logging: progress log entries carry `retry=N`, backoff delay, failure reason; first failure logs `FAIL`, subsequent ones log `RETRY`.
- [ ] **D10 · #40** `--aspect-ratio` flag on `brandly produce`; post-process crop/letterbox step when output ratio ≠ target (2.39:1 default from production bible); document actual output ratio in bible writer.
- [ ] **D11 · #41** `brandly reference` gains `--format` flag; default standardizes on `.jpg` (converts `.png` refs), skips/flags exact duplicate pairs on import; resolution sanity warning.
- [ ] **D12 · #43** New layout (`.brandly/` docs + `pre-production/` + `production/`) adopted by `init`; new `brandly migrate <project>` restructures existing projects (move-only, dry-run preview).
- [ ] **D13** Tests: regression test per deliverable (D1–D12) under `tests/`.
- [ ] **D14** Architecture report (`dev-notes/ARCHITECTURE.md`): structure, module map, data flow, issue→code traceability.

### Definition of Done
- [ ] All 13 issues have a code/doc change that addresses their proposed fixes
- [ ] `PYTHONPATH=src python -m pytest tests/ -q` passes (existing + new tests)
- [ ] `ruff check src/` clean
- [ ] `PYTHONPATH=src python -m brandly_cli --help` runs; new commands (`storyboard`, `migrate`) appear in help
- [ ] Each GitHub issue closed with a comment linking the change
- [ ] `dev-notes/ARCHITECTURE.md` written

### Verification Steps
1. `PYTHONPATH=src python -m pytest tests/ -q` — 0 failures
2. `ruff check src/` — 0 errors
3. `PYTHONPATH=src python -m brandly_cli --help` — new commands listed
4. Per issue: `gh issue view N` checklist items map to committed changes
5. `gh issue close --comment` for #31–#43

### Anti-Drift Rules
- Stay within the proposed fixes named in each issue; do not redesign the CLI surface.
- Do not claim completion without running Verification Steps.
- If an issue is ambiguous or blocked (e.g., Agnes API does not support 2.39:1), report it in the issue comment and implement the fallback (crop/letterbox) — do not silently skip.
- Legacy behavior stays backward compatible: string prompts, old folder layout, and existing projects must still work.

### Estimated Effort
High — ~2–3 focused sessions. Ordering: D1→D2→D3 (prompt core) → D9→D7→D8 (governance, all in `shot_runner.py`/`utils.py`) → D5→D6 (plan-time) → D4 (storyboard) → D11→D10 (assets) → D12 (layout) → D13 (tests) → D14 (report).
