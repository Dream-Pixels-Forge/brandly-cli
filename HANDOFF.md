# HANDOFF — brandly-cli: GOAL-ALL-OPEN-ISSUES (16 open issues)
> Status: **PROGRAM COMPLETE (2026-10-08)** — P1–P6 landed, all 16 issues closed, goal-met audit MET. Kept as the historical record; see PROGRESS.md Rounds 21–26 and `GOAL-ALL-OPEN-ISSUES.md` Program completion notes.

## 1. Current state

**DONE (merged to main @ 1fb9f4d):**
- Goal: `dev-notes/GOAL-ALL-OPEN-ISSUES.md` (16 issues; phases P1–P6). Recon verified → old goal had ASPIRATIONAL `[x]` marks (#251 never done; #247/#258 concept still a stub)
- **P1 (PR #264 → caa8b8c):** #251 (`status --root`), #246/#249 (13 `asyncio.run(` → `run_async`), #250 (gate auto-approve), #248 (`beat_role` wired), #253 (web panels), mypy 31 CI errors cleared (team guards, scenes.REQUIRED_BEATS, production root_path, async_compat returncode), latent `UnboundLocalError: layout` regression fixed (4e3172d shadowed import — see bugs memory)
- **P2 (PR #265 → 1fb9f4d): triage of all 21 failing untracked tests — suite now 0 failed:**
  - **G7 duration truth (keystone):** `run_shots` measures the canonical clip after every successful take, records measured_s/delta_s/duration_status (standard + fallback paths); `get_timeline` two real bugs fixed (hardcoded `Path('.')` instead of root + `completed_ids([])` empty known-set)
  - **G8 continuation take:** `_stitch_clips` (ffmpeg concat demuxer) + bounded continuation takes in `run_shots` (-cont<N> id, identity anchor, history, stitched ships, honest SHORT at bound)
  - **G9 vision gate:** `RunnerConfig.gate_ai` (`off`/`scene-first`/`all`) + `vision_gate_runner`; fail blocks the SCENE (FAIL recorded before OK, scene skipped, other scenes run, exit 1)
  - **G11 UNVERIFIED:** `verify_element` gained `ai_runner` (precedence over API; string verdicts mapped; recorded as `{"verdict": word}`); AI failure → `ai_unavailable` → UNVERIFIED
  - **G12 narrative beats:** `build_scenes` validates beats against `REQUIRED_BEATS`, carries beat, derives duration from `BEAT_DURATIONS` (setup 5/turn 6/consequence 6/resolve 5); no-beat shots keep legacy schema
  - **ALIGNED:** `test_ratio_policy.py::test_run_shots_ignores_legacy_aspect_ratio` — G4 assertion narrowed to ffmpeg transform calls (predates G7; ffprobe read-only measurement allowed) — reason in the goal
  - Survivors committed + lint-cleaned (test_g10/g11/g12/g13, test_f2 ×3: F821 Any, 15× F841, dup clip_filename, B007/B011, whitespace; g13's vacuous resume stub made real)
  - `web/pnpm-lock.yaml` deleted + gitignored
- Per-file triage decisions recorded in the goal's P2 section; PROGRESS.md Rounds 22–23
- **P3 (commit `7bf5546` on main, CI all green — run 37821484237): the document chain is real:**
  - #259 trends: `research_trends` receives the project's style (never hardcoded "commercial"); the phase writes non-empty `docs/plan/trends.md`
  - #258 concept: `DirectorConfig.agent_runner` (Callable[[str], str]); derives the concept from the project brief, writes `docs/plan/concept.md`, moodboard honestly labelled optional; without a runner/brief fails honestly (G11)
  - `_check_phase_artifacts` concept case: `approve <id> concept` fails closed (exit 1) on missing/empty concept.md
  - #257 script: reads `docs/plan/concept.md` (fail-closed with resume hint); prompts compose from the brief (action) + concept content lines (environment) — hardcoded demo strings gone; beat-duration derivation untouched; the G12 beat variation now COMPOSES with the caller's action/setting (no longer clobbers)
  - `PHASE_HANDOFF_SPECS` matches delivered behavior; aligned tracked tests (test_pipeline_orchestration: stub test → concept-without-runner fail-honest; `_write_concept` helper; test_issue_g12)
  - **PROCESS NOTE:** `7bf5546` landed via a DIRECT PUSH to main (the PR #265 merge checked main out; commit+push happened on main unnoticed). CI runs on push to main as well → all green; break recorded in PROGRESS.md Round 24. **Next sessions: ALWAYS `git branch --show-current` before committing.**
- Suite: **1498 passed / 0 failed / 1 skipped** (Windows-only platform skip) · ruff `src/ tests/` clean · mypy clean (5 pre-existing PIL local-only)
- **P4 (commit `5d2eb18` on main, CI green — run 37845861187): audio + publish truth:**
  - #260 audio: music duration derives from scenes.json scene durations (hardcoded `duration=30` gone); the music is DOWNLOADED into `production/<id>/audio/music.mp3` (fail-honest)
  - #260 re_edit mix: ffmpeg `-map 0:v:0 -map 1:a:0 -c:v copy -shortest` mixes the music into `final.mp4`; mix failure fails closed; no music → silent final ships
  - #255 publish: `_publish_platforms` derives platforms from `target_platforms` (`all` → full set; instagram/youtube/facebook → variants; empty fails closed) — hardcoded tuple gone
  - `PHASE_HANDOFF_SPECS`: audio outputs honest (music only — SFX/voiceover removed), publish = real platform contract
  - **REAL BUG:** `async_run_ffmpeg` is a SYNC dual-context helper — an `await` on it (masked by an async test fake) would have broken the mix at runtime; caught by the full-src mypy run
  - Aligned: test_publish_phase_exports_platforms + the full-pipeline test (platforms derive from the project)
- Suite: **1507 passed / 0 failed / 1 skipped** · ruff clean · mypy clean (5 PIL local-only)

## 2. Remaining work (in order)

1. **P5 — agent manifest** (#256): RED tests first (`tests/test_agent_surface_controls.py`): `brandly tools --json` lists the 7 control tools (init, status, progress, approve, estimate, record_cost, memory — mapped to EXISTING commands); status/progress/estimate read-only; approve NOT read-only (human gate); MCP tools/list serves them. Then add the tools to `agent_surface.CLI_TOOLS`.
2. **P6 — close #261 + goal-met audit** (independent auditor, MET required).
3. **Untracked non-test cleanup**: `demo/`, `dev-notes/handoff/`, `GOAL-PIPELINE-DEMO.md`, old `GOAL-OPEN-ISSUES.md`, `HANDOFF.md` — commit or remove deliberately (`git status --short tests/` is already clean).

**NEXT COMMAND:** `sed -n "$(grep -n '^### P5' dev-notes/GOAL-ALL-OPEN-ISSUES.md | cut -d: -f1),+35p" dev-notes/GOAL-ALL-OPEN-ISSUES.md` — then RED tests first.

## 3. Verified ground truth (MUST carry forward)

- **`python` is not on PATH — use `python3`.** mypy NOT preinstalled in fresh shells: `pip install --break-system-packages mypy`.
- **After ANY change, re-run FULL-src mypy** (`python3 -m mypy src/brandly_cli/`), not just the changed file — the G12 scenes.py dict-inference error was caught by CI only because I skipped the full run. CI has no PIL mypy noise (its Pillow env has stubs); local shows 5 pre-existing PIL import-untyped errors — never block on those, fix only what CI reports.
- **`git reset --hard` wipes uncommitted tracked-file edits** — the Round 22 PROGRESS.md entry was lost this way (HANDOFF.md survived as untracked). Commit ledger edits BEFORE resetting/switching, or keep them untracked until commit.
- **Worktree comparisons are invalid when the venv is editable-installed against this src** (Round 21 trap) — `git worktree add` + pytest there still runs THIS src. To test a past commit: `git stash` + `git checkout <ref> -- <file>` + run + restore, or fix PYTHONPATH.
- **`git stash` stashes nothing on a clean tree** — it is not a valid "pre-fix" comparison by itself.
- **AGNES_API_KEY IS set in this environment** — gate tests that assume "no AI" must inject an `ai_runner` or unset the key; the API path engages otherwise (500s on fake bytes → exception → UNVERIFIED after G11).
- **c2112ae lesson (twice):** mechanical edits around imports are dangerous — a redundant local import shadows the module-level one (UnboundLocalError on other paths). Verify imports after every mechanical edit.
- **`_resolve_team` (cmd/team.py) already exits(1) "Team not found"** when the file is missing — `load_team` returning None means the file EXISTS but is corrupt. Guard messages must say corrupt (data honesty).
- **Old goal `[x]` marks were aspirational in places** — always verify against code (`grep`), never trust the checkbox.
- **Two shipped contracts can conflict** (G4 no-shellout test vs G7 ffprobe measurement) — align the test to the narrower intent and record the reason (never game the test, never bulk-relax).
- **`ProjectData` has `model_config = {"extra": "allow"}`** — `primary_reference` is an extra attr; `_load_project_reference` (cli.py:116) reads it via `getattr`.
- **`--root` resolution:** `_get_root(ctx)` reads `ctx.obj["root"]` (global `--root`) → `$ROOT` → walk-up → cwd. Per-command `--root` sets `ctx.obj["root"]` first.
- **`human_review_gate` (gates.py):** `ai_verdict="pass"` + `ai_score >= ai_threshold` (default 90) → auto-approve; callers pass `ai_verdict=gate_result.status` (string, not result.ai).
- **`scenes.REQUIRED_BEATS`** = frozenset({"setup","turn","consequence","resolve"}); **`scenes.BEAT_DURATIONS`** = setup 5 / turn 6 / consequence 6 / resolve 5.
- **wmux not running** — subagent dispatch via A2A unavailable; work directly with TDD.
- **`gh issue view` needs `--json <fields> --template '...'`** (plain view errors on GraphQL deprecation).
- **Test baseline:** pre-program 1439/24 → P1 1457/23 → post-P2 **1488 passed / 0 failed / 1 skipped**.
- **Web bundle:** `web/` (npm, oxlint, vite) → `src/brandly_cli/web/static/`; freshness gate = `git diff --exit-code` on that dir after commit.
- **CI quality job:** version-check → ruff Lint → import-linter → mypy (3.10/3.11/3.12 matrix) → pytest; `web-quality` separate. **ALL GREEN @ 1fb9f4d.**

## 4. Files changed this program (P1 + P2, all merged)

- P1 (`caa8b8c`): cmd/team.py (new + guards), team.py, cmd/plugin.py, plugin_system.py, cmd/production.py, cmd/generation.py, gates.py, video_prompts.py, project_manager.py, scenes.py, async_compat.py, cmd/__init__.py, web panels + bundle, tests (open_issues_p1, reference_detection_logic, team, plugin_system, mypy_union_guards)
- P2 (`1fb9f4d`): shot_runner.py (G7/G8/G9: _measure_and_maybe_continue, _stitch_clips, gate wiring, get_timeline fixes), quality_gate.py (G11 ai_runner + UNVERIFIED), scenes.py (G12 beats + BEAT_DURATIONS), test_ratio_policy.py (G4 alignment), tests: g7/g8/g9/g10/g11/g12/g13 + f2 ×3 committed & lint-cleaned, .gitignore

## 5. How to verify when you land

```bash
git pull && git log --oneline -4   # expect 5d2eb18 (P4) on top
python3 -m pytest tests/ -q --ignore=tests/test_architecture_contracts.py
# expect: 1507 passed / 0 failed / 1 skipped
python3 -m mypy src/brandly_cli/ 2>&1 | tail -1   # expect 5 PIL-only errors (CI-clean)
ruff check src/ tests/ 2>&1 | tail -1             # All checks passed
```

## 6. Goal spec & verdict

- Goal: `dev-notes/GOAL-ALL-OPEN-ISSUES.md` — all 16 open issues, phases P1–P6
- DoD: per-phase in the goal; program = 0 open issues, 0 failed suite, all gates green, goal-met audit MET
- Verdict: **IN PROGRESS** — P1–P4 DONE, P5–P6 pending

## 7. Environment facts

- Node v24 / pnpm 11.5.1; web uses npm (`npm --prefix web run lint/build`)
- Python 3.12.3 → use `python3`; mypy via `pip install --break-system-packages mypy`
- On `main` @ `5d2eb18` (P4 direct-push landed, CI green); repo `/home/dimona/Dream-Pixels-Forge/Dev/cli/brandly-cli`
- **ALWAYS `git branch --show-current` before committing** — after a `gh pr merge --delete-branch` git checks main out; committing there pushes straight to main
