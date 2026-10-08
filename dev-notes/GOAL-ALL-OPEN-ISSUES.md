# GOAL — Fix all 16 open issues: land in-flight fixes, pipeline document chain, audio/publish truth, agent manifest, web data honesty

> **Project:** brandly-cli · **Created:** goal-writer session (2026-10-08)
> **Base:** branch `fix/f2-reference-injection-245-252` @ `4e3172d` (= `origin/main` @ `f632931` + the #245/#252 reference-injection commit)
> **Evidence:** `gh issue list` (16 open issues: #245–#253 + #255–#261) + every issue body fetched 2026-10-08 + working-tree recon below
> **Convention:** every increment is RED → GREEN (contract/pytest test first),
> subagent-executable, subagent-verified (goal-met audit, independent of executor).

## Program Objective

Resolve all 16 open GitHub issues so the automated pipeline
(`brandly run --execute`) completes end-to-end — through `concept` (currently
dead at phase 3), with a real document chain (`trends.md → concept.md →
shots.json`), music actually mixed into `final.mp4`, publish honoring the
user's target platforms, pipeline-control tools discoverable in the agent
manifest, and a web UI that never wires no-ops or fabricates data.

**North star (unchanged):** agents drive it; cinema is the core bone.

## Program Context — verified working-tree state (2026-10-08)

Branch `fix/f2-reference-injection-245-252` @ `4e3172d` + uncommitted work.
Recon findings (all verified by command, not assumed):

| Item | State | Evidence |
|---|---|---|
| `origin/main` @ `f632931` | PR #263 (async_compat.py + 16 conversions in generation.py/project_manager.py) + PR #254 merged | `git show f632931 --stat` |
| #246/#249 on main | **PARTIALLY fixed** — `cmd/production.py` on main still has ~15 `asyncio.run(` sites; the `--execute` pipeline runner can still hit asyncio.run-inside-running-loop | `git show origin/main:src/brandly_cli/cmd/production.py \| grep -c "asyncio.run("` → 15 |
| Working tree `production.py` | ALL 13 `asyncio.run(` sites converted to `run_async` (completes #246/#249 for the pipeline path) — **uncommitted** | `grep -c "asyncio.run(" src/brandly_cli/cmd/production.py` → 0 |
| Working tree `gates.py` | `human_review_gate` gains `ai_verdict`/`ai_score`/`ai_threshold` + auto-approve on AI pass ≥ threshold (#250) — **uncommitted** | `git diff src/brandly_cli/gates.py` |
| Working tree `cmd/generation.py` | reference-discovery fallback restructure + `gate_result` wiring into the human gate (#250/#245/#252) — **uncommitted** | `git diff src/brandly_cli/cmd/generation.py` |
| Working tree `video_prompts.py` | `beat_role` param + per-beat action/setting variations added to `build_single_shot_prompt` (#248) — **DEAD CODE: no caller passes `beat_role`** (`production.py:2720` calls it without `beat_role=beat` even though `beat` is in scope) | `grep -n "beat_role" src/brandly_cli/cmd/generation.py` → no hits; caller inspected |
| Working tree `cli.py` | `get_params` override on `_LazyCommandGroup` — ensures registration before param lookup (`--help`/`--root` resolution) — **uncommitted** | `git diff src/brandly_cli/cli.py` |
| Working tree web files | `PropsInspectorPanel.tsx` + `TimelineTrackHeader.tsx` fixes (#253, partial) — **uncommitted** | `git diff web/src/` |
| `web/static` bundle | old `index-CB9p882h.js` deleted, new `index-DlXfHZIm.js` untracked — **bundle freshness gate red until rebuilt** | `git status --short -- src/brandly_cli/web/static/` |
| `cmd/__init__.py` | was broken (imported non-existent `brandly_cli.cmd.agent_surface` — broke ALL test collection); **REPAIRED this session** to the committed convention + plugin/team registered | `python3 -c "from brandly_cli.cmd import register"` → OK |
| `tests/test_reference_detection_logic.py` | had broken DEBUG prints (IndentationError) + missing mkdir; **REPAIRED this session** — 3/3 passing | `pytest tests/test_reference_detection_logic.py -q` → 3 passed |
| Junk files | `=2.0`, `*.bak`, `*.debug` — **removed this session** | `ls src/brandly_cli/cmd/*.bak` → none |
| Suite baseline | **1439 passed / 24 failed / 1 skipped** (excl. `test_architecture_contracts.py` — needs `importlinter`, env-missing) | `pytest tests/ -q --ignore=tests/test_architecture_contracts.py` |
| The 24 failures | ALL from **untracked** test files (`test_g7_duration_truth`, `test_g8_continuation`, `test_g9_vision_gate`, `test_g10_scorecard_rework`, `test_g11_fail_honest`, `test_g12_narrative_beats`, `test_issues_31_43`, `test_production_plan`) — aspirational RED tests for behavior never implemented on main (e.g. `verify_element` returning `UNVERIFIED` when no AI — code returns `warn`) | stash test: same 14 failures without uncommitted changes |
| Concept phase | **STILL A STUB** — `production.py:2690` returns "concept phase is not implemented yet" (the old goal's F6 `[x]` marks were aspirational, code never changed) | `grep -n "concept phase is not implemented" src/brandly_cli/cmd/production.py` |

## Issue map (16 open)

| # | Type | One-line symptom | Phase below |
|---|------|------------------|-------------|
| 246 | bug, high | `asyncio.run()` inside running loop blocks all video generation (`--execute`) | P1 |
| 249 | bug | `ProjectManager.read` coroutine never awaited (production.py contexts) | P1 |
| 245 | bug, high | asset phase warns "No primary reference" despite approved reference | P1 |
| 252 | bug, high | same root as #245 — one fix, two closes | P1 |
| 250 | enhancement | reference gate prompts Y/n twice even when AI verdict is pass | P1 |
| 248 | bug | 10 shots → near-identical prompts (implementation exists but caller never passes `beat_role`) | P1 |
| 253 | audit | web UI: CFG slider corrupts clip volume, no-op M/S buttons, fabricated seed/checkbox data, dead help button | P1 |
| 247 | enhancement | concept phase not implemented (blocks trends→script) | P3 |
| 258 | audit | concept phase not implemented + `approve` has no concept artifact check — pipeline dead at phase 3 | P3 |
| 259 | audit | trends writes no `docs/plan/trends.md`, hardcodes category `commercial` | P3 |
| 257 | audit | script ignores declared inputs (concept.md, moodboard, brief) — hardcoded action/environment | P3 |
| 260 | audit | audio phase music-only stub — never downloaded, no SFX/VO, music never mixed into `final.mp4` | P4 |
| 255 | audit | publish hardcodes platforms (`tiktok`, `youtube_standard`) — user selection silently dropped | P4 |
| 256 | audit | agent tool manifest missing pipeline-control tools (init, status, progress, approve, estimate, record_cost, memory) | P5 |
| 261 | map | pipeline explained — implementer map; closes when P1–P5 land | P6 |

## Sequencing (hard order)

All phases run on the current branch `fix/f2-reference-injection-245-252`
(it already carries the #245/#252 fix and the in-flight work). Each phase is
its own commit; the branch merges as PR(s) with CI green at the phase gates.

## Phases

### P1 — Land the in-flight fixes: async, reference injection, gate auto-approve, beat wiring, web honesty (#246, #249, #245, #252, #250, #248, #253)

**Objective:** Commit the verified in-flight work with RED-first proof for
every fix, wire the missing `beat_role` caller, rebuild the web bundle, and
close 7 issues in one PR.

**Deliverables**
- [x] Junk cleaned (`=2.0`, `*.bak`, `*.debug`) + `cmd/__init__.py` repaired to committed convention + `tests/test_reference_detection_logic.py` repaired (3/3 green) — done this session, evidence above
- [ ] RED-first proof for the in-flight fixes: stash the fix → observe the new test FAIL → unstash → observe GREEN, for each of:
  - `gates.py` auto-approve (#250): test — `human_review_gate(..., ai_verdict="pass", ai_score=92)` returns `(True, "")` with no prompt; below threshold still prompts/fails-honest
  - `production.py` run_async (#246/#249): source-contract test — no `asyncio.run(` in `cmd/production.py` (all calls go through `async_compat.run_async`)
  - reference discovery (#245/#252): test — `_load_project_reference` / asset-phase resolution finds the approved reference from v2 layout (`pre-production/<id>/<category>/`) via `primary_reference` metadata
  - beat variation (#248): test — after the caller wiring (next bullet), 4+ shots spanning ≥3 beat roles produce distinct per-beat action/setting segments; global style block stays shared
- [ ] **Wire `beat_role` into the script-phase caller**: `production.py:~2720` passes `beat_role=beat` to `build_single_shot_prompt` (the `beat` variable is already in scope; without this the #248 implementation is dead code)
- [ ] Web bundle: `npm --prefix web run lint` (0/0) + `npm --prefix web run build` → fresh `src/brandly_cli/web/static/` (`git diff --exit-code -- src/brandly_cli/web/static/` clean, no stale hashes)
- [ ] Full suite: **zero NEW failures** vs the 1439-passed/24-failed baseline (the 24 pre-existing untracked-test failures are triaged in P2, never papered over)

**Definition of Done**
- [ ] Every in-flight fix has a test that failed on the stash and passed on the tree
- [ ] `beat_role` wired; #248 repro (10-shot project) shows per-beat variation
- [ ] Bundle freshness gate green
- [ ] `ruff check src/ tests/` clean
- [ ] PR merged (CI green: quality 3.10/3.11/3.12 + web-quality); issues #245, #246, #249, #250, #252 closed with the fix reference; #248 closed only after the wiring is verified

**Verification Steps**
1. `python3 -m pytest tests/test_open_issues_p1.py -q` — green (new RED-first contract tests)
2. `grep -n "asyncio.run(" src/brandly_cli/cmd/production.py` — zero hits
3. `grep -n "beat_role=beat" src/brandly_cli/cmd/production.py` — the caller passes it
4. `git diff --exit-code -- src/brandly_cli/web/static/` — clean
5. `python3 -m pytest tests/ -q --ignore=tests/test_architecture_contracts.py` — ≤24 failures (baseline), 1439+ passed

**Anti-drift:** land ONLY the verified in-flight work + the beat wiring; no new features; do not touch the phase machine (P3/P4 do that); do not "fix" the 24 untracked-test failures here (P2).

---

### P2 — Triage the 24 failing untracked tests (#goal-hygiene, no issue)

**Objective:** Every untracked test file either passes, is aligned to the
shipped behavior, or is deleted with a documented reason — no red tests left
on the branch.

**Deliverables**
- [ ] Per-file triage recorded (implement / align / delete + reason) in this goal's completion notes:
  - `test_g11_fail_honest.py` — expects `verify_element` to return `UNVERIFIED` (not `warn`) when AI requested but unavailable. DECISION DEFAULT: implement (matches the already-shipped G11 philosophy "UNVERIFIED is never PASS"; the literal exists in `quality_gate.py:37` but `verify_element` never returns it) — RED first.
  - `test_g7_duration_truth.py`, `test_g8_continuation.py`, `test_g9_vision_gate.py`, `test_g10_scorecard_rework.py`, `test_g12_narrative_beats.py`, `test_g13_quota_aware.py` — triage each failure: if the behavior is genuinely missing and part of the shipped G7–G13 contract, implement it (RED first); if the test contradicts shipped behavior, align the test and document why.
  - `test_issues_31_43.py::test_sync_production_state`, `test_production_plan.py::TestKeyframeArchiving` — triage (likely side effects of the run_async conversions or layout changes — verify which is true).
- [ ] Untracked test files that survive triage are committed (they are currently invisible to CI)
- [ ] `web/pnpm-lock.yaml` — this repo is npm-managed (AGENTS.md gates use `npm --prefix web`); delete it or add to `.gitignore` with a note (do not leave an untracked pnpm lock in an npm repo)

**Definition of Done**
- [ ] `python3 -m pytest tests/ -q --ignore=tests/test_architecture_contracts.py` — **0 failed** (or every remaining failure has a written, reviewed justification)
- [ ] No untracked test files remain (`git status --short tests/` clean)
- [ ] `ruff check src/ tests/` clean

**Verification Steps**
1. `python3 -m pytest tests/ -q --ignore=tests/test_architecture_contracts.py` — 0 failed
2. `git status --short tests/` — no `??` entries
3. Every implement/align/delete decision has a one-line reason in the completion notes

**Anti-drift:** triage is per-test with reasons; never bulk-delete failing tests to get green; never implement behavior that contradicts a shipped contract (align the test instead and say why).

---

### P3 — Pipeline document chain: concept → trends → script (#258, #247, #259, #257)

**Objective:** The `trends.md → concept.md → shots.json` chain becomes real:
trends writes its document and uses the project category; concept derives
from the brief (fail-honest); script reads concept.md and the brief instead
of hardcoded action/environment strings; `approve concept` fails closed on a
missing artifact.

**Deliverables**
- [ ] RED tests first (`tests/test_pipeline_doc_chain.py` or per-issue files):
  - #259: trends phase writes non-empty `docs/plan/trends.md` + passes the project's style/category into `research_trends` (not hardcoded `"commercial"`)
  - #258: concept phase (with a mocked agent runner injected) writes `docs/plan/concept.md` and completes; without an agent/API key it fails honestly (G11 — never fake-pass); `_check_phase_artifacts` gains a `concept` case — `brandly approve <id> concept` fails closed (exit ≠ 0) when `docs/plan/concept.md` is missing/empty
  - #247: `run --execute --until script --yes` progresses past concept with the mocked runner (no "not implemented yet")
  - #257: script phase reads `docs/plan/concept.md` (fail-closed with a resume hint when missing, mirroring the asset phase's shots.json pattern) and composes shot prompts from the brief/concept instead of the hardcoded `action="demonstrates key features"` / `environment="clean studio setting"`
- [ ] Implement the trends worker changes (write doc + real category + gate alignment)
- [ ] Implement the concept phase worker (`_run_phase_real("concept")` — derive concept from `project.json` brief via the agent runner; write `docs/plan/concept.md`; moodboard honestly labelled optional)
- [ ] Add the `concept` case to `_check_phase_artifacts` (cli.py:328-364 region)
- [ ] Implement the script phase input consumption (read concept.md + brief; keep beat-duration derivation untouched — ratified)
- [ ] Update `PHASE_HANDOFF_SPECS`/`phase_handoffs` so spec text matches delivered behavior (never leave the two divergent — per #261 implementer notes)
- [ ] `director_plan`/`phase_handoffs` surface the honest state (concept implemented → normal next_command; the escape `brandly approve <id> concept` remains only as the escalation path after MAX_PHASE_ATTEMPTS)

**Definition of Done**
- [ ] New tests pass RED→GREEN; full suite zero NEW failures vs the P1-end baseline
- [ ] Manual (mocked-agent) repro: `run --execute --until script --yes` passes trends → concept → script
- [ ] `brandly approve <id> concept` on a project with no concept.md fails closed
- [ ] `brandly plan <id> --json` handoff table matches the delivered behavior for all three phases
- [ ] `ruff` clean; CI green

**Verification Steps**
1. `python3 -m pytest tests/test_pipeline_doc_chain.py tests/test_phase_handoffs.py tests/test_pipeline_orchestration.py -q` — green
2. Grep the hardcoded strings: `grep -n "demonstrates key features" src/brandly_cli/cmd/production.py` — no longer the unconditional action source
3. Manual repro of #258's failure — no "concept phase is not implemented yet" with a runner injected
4. `brandly plan <id> --json` — trends/concept/script rows show real inputs/outputs

**Anti-drift:** concept implementation is per issue option 1 (derive with agent, fail-honest without); the auto-approve alternative is REJECTED (violates G11); do not touch beat-duration derivation; do not touch the audio/publish phases (P4).

---

### P4 — Audio + publish truth (#260, #255)

**Objective:** The audio phase produces a real downloaded asset and the
generated music is mixed into `final.mp4`; publish derives platforms from the
project's stored target-platform selection.

**Deliverables**
- [ ] RED tests first:
  - #260: audio phase downloads the generated music into `production/<id>/audio/` (mocked `generate_music` + `download_file`); music duration derives from `scenes.json` scene durations (not hardcoded 30s); `re_edit` attaches the audio track to `final.mp4` (mocked ffmpeg — assert the mix command includes the audio input) or a dedicated mix step does; SFX/voiceover honestly removed from the handoff spec outputs if they stay unimplemented
  - #255: publish derives the platform list from the project's target-platform selection (`project.json`), mapping `all` → the full set; per-platform fail-closed behavior preserved; handoff gate text aligned with what is actually checked
- [ ] Implement the audio worker changes (download + duration derivation)
- [ ] Implement the audio mix into `re_edit` (or the dedicated mix step)
- [ ] Implement the publish platform derivation (`production.py:~3018` — no hardcoded tuple)
- [ ] Update `PHASE_HANDOFF_SPECS` for audio (honest outputs) and publish (real platform contract)

**Definition of Done**
- [ ] New tests pass RED→GREEN; full suite zero NEW failures
- [ ] Audio phase lands a file under `production/<id>/audio/` (mocked e2e proof)
- [ ] `final.mp4` mix includes the music track (mocked-ffmpeg assertion)
- [ ] A project targeting `instagram`/`all` produces Instagram deliverables (mocked export)
- [ ] `ruff` clean; CI green

**Verification Steps**
1. `python3 -m pytest tests/test_audio_publish_truth.py -q` — green (new file)
2. `grep -n '"tiktok", "youtube_standard"' src/brandly_cli/cmd/production.py` — no hardcoded publish tuple remains
3. `grep -n "duration=30" src/brandly_cli/cmd/production.py` — no hardcoded music duration in the audio worker
4. `brandly plan <id> --json` — audio/publish rows match delivered behavior

**Anti-drift:** per-platform fail-closed behavior is preserved; if SFX/voiceover stay unimplemented they are REMOVED from the spec outputs (honesty), never faked; do not touch the publish exit codes beyond aligning text with checks.

---

### P5 — Agent tool manifest: pipeline-control tools (#256)

**Objective:** The agent tool manifest exposes the pipeline-control commands
the Director prompt requires — `init`, `status`, `progress`, `approve`,
`estimate`, `record_cost`, `memory` — mapped to existing CLI commands (no new
implementation, per the `agent_surface` module's design: the tool surface IS
the CLI surface).

**Deliverables**
- [ ] RED tests first (`tests/test_agent_surface_controls.py`): `brandly tools --json` lists the 7 control tools; `status`/`progress`/`estimate` classified read-only; `approve` NOT read-only (human gate); each tool shells out to the real CLI command
- [ ] Add the 7 tools to the `agent_surface.CLI_TOOLS` manifest (mapping existing commands)
- [ ] MCP `tools/list` serves them (the manifest is the single source)

**Definition of Done**
- [ ] New tests pass RED→GREEN; existing agent_surface tests still pass
- [ ] `brandly tools --json` shows 22 tools (15 + 7) with correct read-only flags
- [ ] `ruff` clean; CI green

**Verification Steps**
1. `python3 -m pytest tests/test_agent_surface_controls.py tests/test_agent_tools.py -q` — green
2. `brandly tools --json | grep -o '"name": "[a-z_]*"'` — includes init, status, progress, approve, estimate, record_cost, memory
3. Manual: `brandly tools --json` count == 22

**Anti-drift:** mapping existing commands only — no new implementation, no new CLI flags; read-only classification follows the module's existing convention.

---

### P6 — Close #261 + program close (goal-met audit)

**Objective:** The implementer-map issue closes with the landed fixes; the
program is independently audited.

**Deliverables**
- [ ] All merged PRs reference the issues they close (`Fixes #N` — #261 closes after P1–P5)
- [ ] `gh issue list --state open` — none of the 16 remain
- [ ] PROGRESS.md round entry written (P1–P6 outcomes)
- [ ] goal-met audit: verdict **MET** (independent auditor re-runs every Verification Step above)

**Definition of Done**
- [ ] 0 open issues from the set #245–#253 + #255–#261
- [ ] 0 open fix branches
- [ ] Full suite green; ruff clean; web gates green
- [ ] goal-met audit returns MET (stored with this goal)

**Verification Steps**
1. `gh issue list --state open | grep -E "245|246|247|248|249|250|251|252|253|255|256|257|258|259|260|261"` — no output
2. `gh pr list --state open` — no unmerged fix branches
3. goal-met audit report stored alongside this goal

**Anti-drift:** the auditor is independent of the executor; re-run, don't read; verdicts are binary and block on gaps.

## Program Definition of Done

- [ ] P1–P6 all complete (each with its DoD met)
- [ ] All 16 issues CLOSED with fix references
- [ ] Full suite on the merged branch: **0 failed** (or every remaining failure justified in writing) + ruff clean + web gates green (lint 0/0, build, bundle freshness)
- [ ] goal-met audit: **MET** (independent, re-runs every verification step)

## Verification Steps (program level)

1. `gh issue list --state open` — none of the 16 remain
2. `python3 -m pytest tests/ -q --ignore=tests/test_architecture_contracts.py` — 0 failed
3. `cd web && npm run lint && npm run build` — green; bundle freshness `git diff --exit-code -- src/brandly_cli/web/static/`
4. `ruff check src/ tests/` — clean
5. `brandly tools --json` — 22 tools including the 7 control tools
6. Manual pipeline (mocked-agent): `init → trends → concept → script → asset → audio → re_edit → validate → publish → done` — completes; music mixed; platforms honored

## Anti-Drift Rules (program level)

- Stay within the 16 issues + the P2 test-hygiene item. New findings get NEW issues, not silent scope growth.
- RED → GREEN for every increment; no code without a failing test first (in-flight fixes get their RED proof via stash → observe → unstash).
- Never fabricate telemetry, gate verdicts, or UI data (fail-honest G11 stands).
- One fix closes #245 + #252 together; #246 + #249 together (same roots).
- Do not touch the ratified beat-duration derivation or the frozen design spec (`dev-notes/DESIGN-STUDIO-SHELL.md`).
- `PHASE_HANDOFF_SPECS` is the contract agents read — deliver what the spec says or correct the spec. Never leave the two divergent.
- The state machine (ordering, resume, fail-closed, bounded retries, escalation) is solid — fixes live inside `_run_phase_real` / `_check_phase_artifacts` / the manifest, never in the phase machine.
- If blocked (e.g., no API key for a manual repro), report the blocker — do not work around silently.
- Subagent discipline: executor ≠ auditor; the goal-met audit re-runs evidence.

## Estimated Effort

| Phase | Complexity | Estimate |
|-------|-----------|----------|
| P1 land in-flight fixes | medium (RED-proof + beat wiring + bundle) | 0.5–1 day |
| P2 test triage | medium (24 tests, per-file decisions) | 0.5–1 day |
| P3 document chain | medium–large (3 phases + gate + handoffs) | 1–1.5 days |
| P4 audio + publish | medium (download + mix + platforms) | 0.5–1 day |
| P5 agent manifest | small (7 mappings + tests) | 2–4 h |
| P6 close + audit | small | 1–2 h |
| **Total** | | **~3.5–5.5 days** |
