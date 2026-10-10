# GOAL — Fix all 13 open issues #270–#283: pipeline honesty, reference truth, layout contract, document chain, agent driver, screenplay

> **Project:** brandly-cli · **Created:** pipeline-orchestrator session (2026-10-09)
> **Base:** `main` @ origin (0/0 divergence, tree clean) — verified via
> `git rev-list --left-right --count origin/main...HEAD`
> **Evidence:** `gh issue list` (13 open issues #270–#283) + every issue body
> fetched 2026-10-09 + working-tree recon below (all findings verified by
> command, not assumed)
> **Convention:** every increment is RED → GREEN (contract/pytest test first),
> per `AGENTS.md` §0 + `dev-notes/CONVENTIONS.md` §2; subagent-auditable
> (goal-met audit re-runs evidence, independent of the executor).

## Program Objective

Resolve all 13 open GitHub issues so the automated pipeline
(`brandly run --execute`) is honest end-to-end: no silently-dropped references,
no bricked phase state, no assets landing in the wrong tree, no no-data
documents written as success, no conflicting duration maps, a duration target
that actually drives the film, a concept phase the CLI alone can pass, and a
screenplay producer for the declared-but-unproduced document.

**North star (unchanged):** agents drive it; cinema is the core bone.

## Program Context — verified working-tree state (2026-10-09)

| Item | State | Evidence |
|---|---|---|
| Branch | `main`, in sync with origin (0/0), clean tree | `git status --short`, `git rev-list --left-right --count` |
| #270 root cause | `generation.py:2340` `_sync_project` writes `current_phase="video"` — not in `PHASE_ORDER` (constants.py:79); 3 unguarded `.index()` sites (production.py:3290 `run_pipeline`, :363 `run`, :531 `approve`) | read |
| #271 root cause | `cli.py:125` `_load_project_reference` bare `asyncio.run(` → swallowed → GOLD reference silently dropped on the pipeline path (RuntimeWarning fired live) | read; reachable from `run_async(director.run_pipeline)` |
| #271 audit | bare `asyncio.run(` sites reachable from running-loop contexts: **cli.py:125** (pipeline path) + **agent_tools.py:52,84,107,128,236** (handlers run inside `agent_tool_loop`'s running loop — every built-in tool call from `agnes-chat --tools` fails with `{"error": RuntimeError}` today); **web/state.py:213 `compute_quality_status`** and **web/utils/ffprobe.py:36 `get_clip_info`** have NO callers (dead but broken-by-construction — converted defensively, reason recorded). All remaining bare sites (post.py, team.py, providers.py, tools.py, io.py, gate.py, cost_tracker.py, cli.py:322) are CLI-thread-context — `asyncio.run` is safe there | grep + read |
| #272 root cause | `generation.py:~902` `dest = Path(output).expanduser()` — relative `--output` resolves against the CLI cwd, ignoring `--root` (the only path that bypasses root resolution) | read |
| #273 root cause | trends phase passes `proj.style` as the research category; `TREND_DATABASE` keys are product categories (`beauty/fashion/fitness/food/tech`) — a style like `cinematic` matches nothing → empty document written as success | read trends.py:146 |
| #274 root cause | `production.py:2839` local `beat_durations {setup:4, turn:5, consequence:5, resolve:6}` conflicts with `scenes.BEAT_DURATIONS {setup:5, turn:6, consequence:6, resolve:5}`; `beats[(i-1) % 4]` wraps a 5th shot to `setup` | read |
| #275 root cause | reference command writes `project.primary_reference` (generation.py:~480) BEFORE the quality gate (generation.py:~494) — a gate-FAILED plate is promoted to the identity anchor | read |
| #276 | `init` has no `--target-duration`; `ProjectData` has no `target_duration`/`product_category` fields; a 30s brief yields a 24s shot list unchecked | read types.py ProjectData |
| #277 | `run --execute` constructs `Director(DirectorConfig(root, gate_ai=gate_ai))` (production.py:327) with no `agent_runner` — concept dead-ends without an external agent; `agnes_chat`/`chat_completion` exist as the driver | read |
| #278 | reference docstring claims `.brandly/<id>/images/<category>/` + prefix `reference_<subject_type>_*`; the code writes `pre-production/<id>/<category>/` via `IMAGE_NAME_PREFIXES` (`char_/loc_/prop_`); `reference` lacks `--json` (image has it, #73) | read |
| #280 | `DOC_CATEGORIES` includes `screenplay`; no writer anywhere; `analyze-project` checks against it | grep — no writer |
| #281 | storyboard command SAVE path already resolves the v2 tree (`resolve_media_root → pre-production/<id>/storyboard/` — verified); the DOCSTRING claims the legacy `.brandly/<id>/images/storyboard/`; the pipeline never calls the storyboard step (asset jumps script → video credits) | read production.py:1558+ |
| #283 | `migrate.py:33-34` maps singular→plural (`transition→transitions`, `insert→inserts`) while `layout.VIDEO_CATEGORIES` declares singular and `shot_runner.move_shot_clips` writes singular; only the transition continuation-take is folder-routed — insert/transition clips land in `videos/scenes/` | read |
| Related same-chain defect | `brandly video`'s metadata lookup searches `pre-production/<id>/images/<category>/` with the dead `reference_<subject_type>_` prefix (generation.py:~1470) — the real plate path is `pre-production/<id>/<category>/` with `IMAGE_NAME_PREFIXES` prefixes; today it only works via the `image_path` fallback | read |

## Issue map (13 open)

| # | Type | One-line symptom | Increment |
|---|------|------------------|-----------|
| 270 | bug, high | `current_phase="video"` bricks run/approve/run --execute with a raw ValueError | I1 |
| 271 | bug, high | GOLD reference silently dropped on the pipeline path (bare asyncio.run) | I1 |
| 275 | bug, high | gate-FAILED plate promoted to primary_reference | I2 |
| 282 | bug | wardrobe reference category unreachable from the CLI; no garment-only mode | I2 |
| 272 | bug | `image --output` resolves against the CLI cwd, ignoring --root | I3 |
| 283 | bug | duplicate insert/transition trees; clips never routed to their folder | I3 |
| 281 | bug | storyboard docstring claims the legacy tree; pipeline never generates storyboards | I3 |
| 273 | bug | trends writes an empty document silently (style-as-category mismatch) | I4 |
| 274 | bug | script-phase beat_durations conflicts with scenes.BEAT_DURATIONS; closing shot wrapped to setup | I4 |
| 276 | feat | --target-duration never reaches the pipeline; no film-level duration truth | I4 |
| 277 | feat | run --execute dead-ends at concept — no agent runner wired | I5 |
| 278 | docs/bug | stale save-path/prefix docstrings; reference lacks --json | I5 |
| 280 | feat | screenplay declared but never produced | I6 |

## Increments (hard order) — I1-I6 COMPLETE (see PROGRESS.md Round 27)

### I1 — Async surface + phase-machine honesty (#271, #270)

**Deliverables**
- [x] RED-first contract tests (`tests/test_open_issues_270_283.py`): observed failures on the pre-fix tree
- [x] #271: `cli.py:_load_project_reference` → `run_async`; `agent_tools.py` 5 sites → `run_async` (reachable via `agent_tool_loop`); `web/state.py:compute_quality_status` + `web/utils/ffprobe.py:get_clip_info` converted defensively (no current callers — audit note); all other bare sites audited + recorded as safe CLI-thread context
- [x] #271 (same-chain): `brandly video` metadata lookup uses the real plate path (`resolve_media_root(root, id, "images") / category`) + the real prefix (`layout.image_name_prefix`) — the `images/<category>` depth + `reference_<subject_type>_` prefix dead lookup is corrected
- [x] #270: `generation.py:_sync_project` writes `current_phase="asset"` (the produce runner belongs to the asset phase — never an invalid stage name); the 3 `.index()` sites (production.py `run_pipeline`/`run`/`approve`) guarded fail-honest: a `current_phase` not in `PHASE_ORDER` returns/raises a structured error with a repair hint (G11) — a poisoned state file never crashes the CLI with a raw traceback

**Definition of Done**
- [ ] New tests pass RED→GREEN; full suite zero NEW failures
- [ ] `grep -n "asyncio.run(" src/brandly_cli/cli.py src/brandly_cli/agent_tools.py` — zero bare hits
- [ ] Poisoned `current_phase="video"` fixture: `run`/`approve`/`run --execute` fail honestly (exit 1, structured error, repair hint)
- [ ] `ruff check src/ tests/` clean

### I2 — Reference truth: gate-before-promotion + wardrobe (#275, #282)

**Deliverables**
- [x] #275: `primary_reference` metadata update moves AFTER the quality gate; on gate FAIL the plate is NEVER promoted (metadata skipped, honest warning — the plate stays on disk, un-promoted); on gate pass / no gate the metadata records `gate_status`/`gate_score` so consumers can fail-honest
- [x] #282: `wardrobe` added to `REFERENCE_SUBJECTS` + `--subject-type` choices; a wardrobe template in `reference_prompts.py` (garment-only flat-lay on a neutral backdrop, NO person wearing it, color/material/details legible) → lands in `pre-production/<id>/wardrobe/` with the `wardrobe_` prefix (`image_name_prefix` falls back to the subject type itself)

**Definition of Done**
- [ ] RED-first: a mocked gate-fail reference run leaves `primary_reference` absent; a pass run writes it with the gate verdict recorded
- [ ] `brandly reference <id> --subject-type wardrobe -s "..."` resolves the wardrobe template + wardrobe category
- [ ] Full suite zero NEW failures; ruff clean

### I3 — Layout contract: --output root, folder routing, storyboards (#272, #283, #281)

**Deliverables**
- [x] #272: relative `--output` resolves against the `_get_root(ctx)`-resolved project root (absolute stays absolute); a file written via `brandly --root <tmp> image --output <rel>` lands under `<tmp>/<rel>` and NEVER in the cwd
- [x] #283: `migrate.py` `_VIDEO_CATEGORY_RENAME` deleted — migrate maps to the LAYOUT-declared singular categories (`transition`, `insert`); `shot_runner` routes clips by the shot's `folder`: insert → `videos/insert/`, transition → `videos/transition/`, scene shots → `videos/scenes/` (one convention, no duplicate trees)
- [x] #281: storyboard docstring corrected to the real v2 path `pre-production/<project>/storyboard/` (the save path already resolves v2 — verified; contract test pins it); `ProjectData` gains `storyboards: bool = False`; the asset phase, when `storyboards` is true, runs the keyframe pass first (generate per shot with STORYBOARD_INSTRUCTION → deterministic gate → Scene-XX-Shot-X-Y names into `pre-production/<id>/storyboard/`); a FAILING keyframe blocks that shot's video generation (fail-closed — composition errors caught at image cost, never video cost, per issue #33)

**Definition of Done**
- [ ] RED-first: insert + transition shots produce clips in their respective folders; `migrate` creates no plural trees; the docstring paths match the code's write paths
- [ ] Storyboard contract: keyframes land ONLY under `pre-production/<id>/storyboard/`; a failed keyframe blocks the video spend
- [ ] Full suite zero NEW failures; ruff clean

### I4 — Document chain truth: trends category, beats, target duration (#273, #274, #276)

**Deliverables**
- [x] #273: `ProjectData` gains `product_category: str | None = None`; `init` gains `--category` (product category — choices from `trends.list_categories()`); the trends phase passes `proj.product_category` to `research_trends` (style and category are different axes); no category / category matching nothing in `TREND_DATABASE` → the phase FAILS HONEST with a repair hint (G11 — a zero-format document is never written as success)
- [x] #274: the script phase imports `scenes.BEAT_DURATIONS` (single source — the local conflicting dict is deleted); beat distribution `beats[min(i - 1, len(beats) - 1)]` — cycle until all 4 placed, then repeat the LAST beat; a closing shot is never labeled `setup`
- [x] #276: `ProjectData` gains `target_duration: int | None = None`; `init` gains `--target-duration <seconds>`; the script phase, when a target is set, derives the shot count/durations to HIT it (start from the beat-map durations, distribute the remainder into shots capped at the 6s reliable window; a target below the 3-shot minimum (~15s) or above the 10-shot window (~60s) fails honestly with the proposed plan); `brandly status` reports the film's measured total vs the target (G7-style truth at film level, data-honest)

**Definition of Done**
- [ ] RED-first: a style-only project's trends phase errors (never an empty success); a 5-shot script carries durations identical to `scenes.BEAT_DURATIONS` and never assigns `setup` to the final shot; `init --target-duration 30` → the script shot list sums to ~30s within the window
- [ ] Full suite zero NEW failures; ruff clean

### I5 — Agent driver + CLI surface (#277, #278)

**Deliverables**
- [x] #277: `_agnes_concept_runner` — prompts the Agnes text model via `run_async(chat_completion(...))` (dual-context; fails honestly on no key / empty content per G11); `brandly run --agent-runner [agnes|off]` (default: agnes — the CLI alone drives concept); `Director(DirectorConfig(root, gate_ai=..., agent_runner=...))`
- [x] #278: reference docstring corrected to the real path (`pre-production/<project_id>/<category>/`) + the real prefix (`IMAGE_NAME_PREFIXES`); storyboard docstring corrected to `pre-production/<project>/storyboard/`; `brandly reference --json` added (mirror the image command's success/error JSON shape, #73)

**Definition of Done**
- [ ] RED-first: `--agent-runner off` fails honestly at concept (structured error); the docstring contract test (help text vs layout constants) fails on the stale text
- [ ] `brandly reference ... --json` emits parseable JSON
- [ ] Full suite zero NEW failures; ruff clean

### I6 — Screenplay producer (#280)

**Deliverables**
- [x] Decision (per issue option 1): a `screenplay` phase between concept and script — `PHASE_ORDER` gains `screenplay` (10 → 11 phases); the state machine ordering/resume/fail-closed machinery is untouched (the phase rides the existing machine)
- [x] `_run_phase_real` screenplay case: derive from the brief + concept.md via the agent runner (fail-honest without one — G11), write `docs/plan/screenplay.md` (the core shots of the film; inserts/transitions optional — the Director may add them, see #283's insert/transition routing)
- [x] `_check_phase_artifacts` gains the screenplay case; `PHASE_HANDOFF_SPECS` gains the screenplay entry (trends → concept → screenplay → script); `phase_costs` gains the screenplay row; the script phase treats `docs/plan/screenplay.md` as an optional input
- [x] Tests asserting the 10-phase order are aligned with a recorded reason (10 → 11)

**Definition of Done**
- [ ] RED-first: a project run through the document chain (with a mocked runner) produces a non-empty `screenplay.md`; `brandly plan <id> --json` shows the screenplay row
- [ ] Full suite zero NEW failures; ruff clean

### I7 — Close-out: goal-met audit + ledger + issue closes

**Deliverables**
- [ ] All merged PRs reference the issues they close (`Fixes #N`)
- [ ] `gh issue list --state open` — none of the 13 remain
- [ ] PROGRESS.md round entry written (I1–I7 outcomes)
- [ ] goal-met audit: verdict MET/BLOCKED (independent re-run of every verification step, binary)

## Verification Steps (program level)

1. `python -m pytest tests/ -q` — 0 failed (baseline 1528 passed / 1 skipped)
2. `ruff check src/ tests/` — clean
3. `grep -n "asyncio.run(" src/brandly_cli/cli.py src/brandly_cli/agent_tools.py` — zero bare hits (run_async only)
4. `grep -n '"video"' src/brandly_cli/cmd/generation.py` — no invalid current_phase write
5. Poisoned-state repro: `run`/`approve` exit 1 with a structured repair hint (no traceback)
6. `brandly reference <id> --subject-type wardrobe -s "..."` — resolves; wardrobe template exists
7. `brandly --root <tmp> image --project-id <id> --output <rel>` (from a different cwd) — lands under `<tmp>/<rel>`
8. `migrate` on a legacy project — no `transitions/`+`transition/` duplicates
9. Docstring contract test — help paths/prefixes match layout constants
10. `init --target-duration 30` → script shot durations sum to ~30s; status reports target vs measured
11. `run --execute --until concept --yes` with a key → concept.md non-empty (agnes runner); without → structured error
12. Document chain → `docs/plan/screenplay.md` non-empty; `plan --json` shows the screenplay row
13. Web gates (if web files touched): lint 0/0, build, bundle freshness

## Anti-Drift Rules (program level)

- Stay within the 13 issues + the recorded same-chain defects (video metadata lookup). New findings get NEW issues, not silent scope growth.
- RED → GREEN for every increment; no code without a failing test first.
- Never fabricate telemetry, gate verdicts, or UI data (fail-honest G11 stands).
- Do not touch the frozen design spec (`dev-notes/DESIGN-STUDIO-SHELL.md`); no frontend work is in scope.
- `PHASE_HANDOFF_SPECS` is the contract agents read — deliver what the spec says or correct the spec; never leave the two divergent.
- The state machine (ordering, resume, fail-closed, bounded retries, escalation) is solid — I6 adds a phase to `PHASE_ORDER` per the issue's explicit option; all other fixes live inside `_run_phase_real` / `_check_phase_artifacts` / the workers, never in the machine.
- Do not touch the ratified beat-duration VALUES (`scenes.BEAT_DURATIONS`) — I4 makes the script phase CONSUME them (single source), never re-define them.
- If blocked (e.g. no AGNES_API_KEY for a live repro), report the blocker — mocked runners prove the contract; do not work around silently.
- Executor ≠ auditor; the goal-met audit re-runs evidence.

## Estimated Effort

| Increment | Complexity | Estimate |
|-----------|-----------|----------|
| I1 async + phase machine | medium (2 fixes + guards + audit) | 0.5 day |
| I2 reference truth | medium (gate ordering + wardrobe template) | 0.5 day |
| I3 layout contract | medium-large (3 fixes + storyboard wiring) | 0.5–1 day |
| I4 document chain | medium-large (3 features + derivation) | 1 day |
| I5 agent driver + surface | medium (runner + --json + docs) | 0.5 day |
| I6 screenplay phase | medium (phase add + specs) | 0.5 day |
| I7 close-out | small | 1 h |
| **Total** | | **~3.5–5 days** |

---

## Program close-out (2026-10-10)

- [x] I1–I7 all complete (each with its DoD met)
- [x] All 13 issues CLOSED with fix references — PR #285 (merge `5822a1e`);
      #270 auto-closed by the PR, #271–#283 closed with per-issue fix
      comments (the PR's space-separated `Fixes` line only parsed #270)
- [x] Full suite on the merged branch: **1573 passed / 0 failed** + ruff
      clean + mypy Success (98 files) + import-linter OK + CI green
      (quality 3.10/3.11/3.12 + web-quality, run 38063784628)
- [x] goal-met audit: **MET (confidence high)** — every verification step
      re-run independently on merged main, 2026-10-10

### Goal-met audit results (re-run, not read)

| Step | Result |
|---|---|
| Full suite | **1573 passed / 0 failed** (baseline 1528 + 45 new) |
| ruff src/ tests/ | clean |
| mypy src/ | Success (98 files) |
| import-linter | OK |
| Zero bare `asyncio.run(` (cli.py + agent_tools.py) | 0 hits |
| No invalid `current_phase` write | the write is `"asset"` (the only grep hit is the explanatory comment) |
| Poisoned state (run + approve, live) | exit 1, "not a pipeline phase" + repair hint, no traceback |
| Wardrobe (live) | accepted past the choice validation; garment-only template ("no person") |
| `--root` + relative `--output` (live) | exit 0, landed under the root, cwd clean |
| migrate (live) | no plural trees (`"transitions"`/`"inserts"` gone) |
| `init --target-duration 30` → script (live) | error-free, durations sum **30s**, every shot 4–6s, closing beat `resolve` |
| `run --execute --until concept` (live, agnes mocked) | exit 0, `docs/plan/concept.md` non-empty |
| `--agent-runner off` (live) | exit ≠ 0, structured fail-honest error |
| Document chain (live) | runs to script; `screenplay` in phases_run; `docs/plan/screenplay.md` non-empty |
| CI | quality 3.10/3.11/3.12 + web-quality all PASS (run 38063784628) |
| Open issues / open PRs | 0 / 0 |
