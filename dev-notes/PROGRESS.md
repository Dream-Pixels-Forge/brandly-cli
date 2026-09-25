# Pipeline Progress — brandly-cli

## Current State
- Project: brandly-cli
- Started: 2026-09-07
- Version: 0.3.26 → 0.4.0 (G7 orchestrator + subagent contract layer complete)
- Current Phase: Phase 3 (Engineer) — Feature Implementation
- Status: in-progress (core features complete)
- Test Count: 764 passed
- Lint: clean (ruff + mypy + import-linter)

## Phase Completion
- [x] Phase 0: Bootstrap (AUDIT.md + GOAL.md)
- [ ] Phase 1: Brainstorm (BRAINSTORM.md) — *skipped: existing project*
- [x] Phase 2: Governance (GOAL.md + SECURITY.md + SPEC.md)
- [x] Phase 2.5: Implementation Plan (IMPLEMENTATION.md)
- [in_progress] Phase 3: Engineer (implementation)
  - [in_progress] Phase 3A: Core Pipeline (stitch, export-platforms, thumbnails)
  - [ ] Phase 3B: Quality Enhancements (dubbing, beat-sync, auto-direct, trends)
  - [ ] Phase 3C: Developer Features (analyze, templates, batch, webhook)
  - [ ] Phase 3D: Ecosystem (share, team, plugin)

## Progress Tracking

### Round 1/256 — Initial Assessment & Bug Fix
- [x] Loaded pipeline-orchestrator skill
- [x] Inspected all 19 source modules in brandly-cli
- [x] Ran test suite: 166 passed, 4 failed
- [x] Identified root cause: hardcoded cwd paths in utils.py
- [x] Fixed write_generation_plan, write_generation_doc, _update_plans, detect_project_artifacts
- [x] Updated all 8 call sites in cli.py to pass root parameter
- [x] Re-ran tests: 170/170 passing
- [x] Created dev-notes/AUDIT.md
- [x] Created dev-notes/GOAL.md
- [x] Created dev-notes/PROGRESS.md
- [x] Verified end-to-end CLI workflow (init → run → approve → export)
- [x] Added .github/workflows/ci.yml
- [x] Added .env.example
- [x] Fixed brandly cost graceful fallback for missing cost state
- [x] Bumped version to 0.2.0
- [x] Added pre-commit hooks (.pre-commit-config.yaml + install script)
- [x] Created Makefile with 14 targets (test, lint, ci, e2e, etc.)
- [x] Added SECURITY.md (low-risk assessment)
- [x] Added SPEC.md (full architecture specification)
- [x] Updated .gitignore with .pre-commit-cache/
- [x] All verification gates passing (16/16)

### Round 3/256 — Agent-native pipeline program (GOAL-AGENTIC-PIPELINE.md)

**Current Phase:** Phase 3 (Engineer) — Goal 1 (agent-native tool surface) · **Status:** in-progress

- [x] Loaded `pipeline-orchestrator` + `test-driven-development` skills
- [x] Deep audit of the agentic system → `dev-notes/AUDIT-AGENTIC-PIPELINE.md` (F1–F9)
- [x] Goal program (6 goals, ordered) → `dev-notes/GOAL-AGENTIC-PIPELINE.md`
- [x] Housekeeping: removed phantom `.brandly/untitled` + `.brandly/undefined` (21 files)
- [x] **G1** Agent-native tool surface — COMPLETE (3 PRs)
  - [x] PR 1: `agent_surface.py` dispatch layer + `brandly tools --json` manifest
        (TDD: 21 tests written RED first — verified failing on `ImportError` — then GREEN)
  - [x] PR 2: `brandly mcp serve` (stdio JSON-RPC: initialize / tools/list / tools/call;
        18 tests, real handshake smoke-tested)
  - [x] PR 3: `brandly init` emits `AGENTS.md` (create-only); `brandly sync` raw keys
        behind `--legacy-provider-keys`; README "Driving brandly from an AI tool"
        (9 tests)
- [x] **G2** Real director orchestration (`run --execute`, produce-backed phases, stub removal) — COMPLETE (4 PRs)
  - [x] PR A: `brandly run <id> --execute [--until <phase>] [--yes]` drives
        `Director.run_pipeline` (resumable from `project.phases`); `run_phase`
        fails closed (worker error/exception → phase `failed`, `current_phase`
        frozen, pipeline stops, exit 1); fabricated stubs (`concept`/`asset`/
        `re_edit`/`publish`) report "not implemented" instead of fake success
        (TDD: 11 tests RED → GREEN; `tests/test_pipeline_orchestration.py`)
  - [x] PR B: `script` writes real `shots.json` (scene ids per G3); `asset`
        invokes the produce/shot_runner path
  - [x] PR C (PR #88, squash @ `10b75ea`): `re_edit` stitches the scene clips
        via `stitch.stitch_videos` → `videos/final.mp4` (fail-closed on missing
        manifest/clips); `validate` runs the G3 scene gate
        (`scenes.evaluate_all` + deterministic `verify_element(use_ai=False)`
        runner, off the event loop) and blocks advance on any non-pass verdict;
        `publish` calls `export_platforms` (tiktok + youtube_standard →
        `<project>/export/`, fail-closed on per-platform errors). +11 TDD tests,
        incl. E2E `brandly run --execute` to `done` with mocked
        providers/ffmpeg/gate/exports. Suite 716 → 725 passed; ruff/mypy clean;
        lint-imports KEPT; CI green on #88. Stub parametrization trimmed to
        `concept` (the only remaining honest stub).
  - [x] PR D: `autodirector.auto_direct` removed (fabricated stub, audit
        F3/F4) with a regression test pinning the deletion; `brandly
        director` moved to `cmd/production.py` and now prints the Director
        prompt plus the live orchestrator plan — `director_plan()` is the
        data-only source (phases, per-phase status, current step, exact
        next command: `brandly init` before a project exists,
        `brandly run <id> --execute --yes` from any incomplete state;
        `None` when the pipeline is complete). 10 new TDD tests
        (`tests/test_director_plan.py`); suite 725 → 733 passed;
        ruff/mypy clean; lint-imports KEPT (L1→L0 director-prompt import).
- [x] **G3** Explicit scene model + scene completeness gate (audit F6/F7) — COMPLETE
  - [x] `scenes.py`: `scenes.json` manifest (`docs/plan/`) written by `produce`
        BEFORE generation; project-unique scene ids (S01…) preserve act+number;
        v2-aware roots (pre-production/ + production/); `status()` matrix;
        `evaluate()`/`evaluate_all()` with injected quality runner (L0-pure)
  - [x] `brandly scenes status [--json]`; `brandly gate --scene/--all-scenes
        [--no-quality]` (exit 0/1/2 like the element gate)
  - [x] TDD: 19 tests RED (ImportError) → GREEN; GateResult.status normalized
        (lowercase); import-linter L0 extended
- [ ] **G4** Ratio crop moved to assembly/export
- [ ] **G5** Scope truth pass (`brandly capabilities --json`, honest README)
- [ ] **G6** Publish path (decision-gated)

### Round 4/256 — G7: agentic orchestration — orchestrator + subagent contract layer

**Current Phase:** Phase 3 (Engineer) — Goal G7 (`dev-notes/GOAL-AGENTIC-ORCHESTRATION.md`)

- [x] **PR E** (PR #90, squash @ `da62aff`): `phase_handoffs()` data-only dispatch
      contracts (inputs/outputs/gate/est_cost per phase) + `brandly plan <id>
      [--json]` + `agent_surface` `plan` tool (read-only, MCP-dispatchable);
      `estimate` routed through `phase_costs()`. 13 TDD tests
      (`tests/test_phase_handoffs.py`) RED first (ImportError) → GREEN.
- [x] **PR F** (PR #91, squash @ `21d7578`): Director prompt "Subagent Dispatch"
      section (5-item per-subagent contract, parallel-cognition /
      serialized-execution rule, gate-screening loop); `brandly director`
      dispatch table; `brandly init` AGENTS.md subagent note. 8 TDD tests
      (`tests/test_subagent_dispatch.py`).
- [x] **PR G** (PR #93, squash @ `55139a0`): structured retry envelope + bounded
      phase re-dispatch — `run_phase` persists an `attempts` counter on the
      phase (new `PhaseResult.attempts`), returns a JSON-parseable
      `retry_instruction` (error, attempts/max_attempts, escalate, re-run +
      `brandly approve` commands); cap 3 (`MAX_PHASE_ATTEMPTS`) → escalate;
      `phase_handoffs` / `brandly plan --json` surface attempts + envelope on
      failed phases; `brandly run --execute` failure output gains
      `Retry attempt: N/3` + escalation + JSON block; state-only `run`
      preserves the counter (cap cannot be bypassed). 7 TDD tests
      (`tests/test_retry_envelope.py`) RED first (ImportError) → GREEN.
      Suite 728 → 764 passed; ruff/mypy clean; import-linter KEPT; CI green.

### Round 5/256 — v0.4.0 release round (G7 shipped)

- [x] README: orchestrator + subagent workflow section added to "Driving brandly
      from an AI tool" (plan → dispatch → screen → advance → retry/escalate),
      pointing at `brandly plan <id> --json` as the dispatch source of truth.
- [x] CHANGELOG `[0.4.0]` entry (G7 PR E/F/G + shot-runner crop/rename fix).
- [x] Version bump `pyproject.toml` + `src/brandly_cli/__about__.py` → `0.4.0`
      (release workflow gates tag == pyproject == `__about__`).
- [x] Gates re-run before tagging: 764 passed; ruff/mypy/import-linter clean.
- [x] Tag `v0.4.0` + GitHub release → `release.yml` publishes to PyPI
      (OIDC trusted publishing, `skip-existing: true`). Release:
      https://github.com/Dream-Pixels-Forge/brandly-cli/releases/tag/v0.4.0 —
      workflow success; PyPI endpoint verified (`brandly-cli==0.4.0`, 2 files:
      sdist + wheel). CI (quality 3.10/3.11/3.12 + web-quality) green on `main`
      before tagging.
- [x] Pre-tag local verification: version parity (`pyproject == __about__`),
      full suite 764 passed, and a live CLI smoke (`init` → `plan --json` with
      10 phase handoffs → `director` prompt + dispatch table).
- Rollback point for G7: `git reset --hard v0.3.26` +
      `pip install brandly-cli==0.3.26` restores the pre-G7 release.

### Round 6/256 — Pre-existing defect fixes (CLI entry points + agent runner)

**Branch:** `bug/cli-entrypoints-and-runner-encoding` → PR #94 (squash @ `071bb69`)

- [x] **CLI module entry point** — `python -m brandly_cli.cli` ran `main()`
      before the `cmd.*` groups were registered, so `--help` listed no commands
      and every call failed with `No such command` (`make e2e` was broken).
      Fix: `_LazyCommandGroup` attaches the groups on first command lookup and
      the import-time `register(cli)` call is gone.
- [x] **cli ⇄ cmd import cycle** — importing any `brandly_cli.cmd.<module>`
      *first* raised `ImportError: cannot import name 'register' ... (most
      likely due to a circular import)`; only `import brandly_cli.cli` first
      worked (the suite passed by import-order luck). Fix: dropping the
      import-time `cli → cmd` edge makes every import order valid.
- [x] **Agent runner encoding** — `agent_surface._subprocess_runner` decoded the
      CLI's UTF-8 output with the platform locale codec (cp1252 on Windows) →
      `UnicodeDecodeError` with `stdout=None`, silently losing MCP tool
      results. Fix: explicit `encoding="utf-8", errors="replace"`.
- [x] **Suite warnings** — the 2 upstream starlette/anyio `TestClient`
      warnings are silenced with message-scoped `filterwarnings` entries
      (documented, incl. that `StarletteDeprecationWarning` subclasses
      `UserWarning`); the suite is now warning-free.
- TDD: `tests/test_cli_entrypoints.py` (5 subprocess-level tests) RED first —
      verified failing on the two circular-import `ImportError`s, the
      command-less `--help`, and the `None` stdout — then GREEN. Suite 764 →
      769 passed, 0 warnings; ruff/mypy/import-linter clean; CI green on #94
      (quality 3.10/3.11/3.12 + web-quality).
- Not in scope (separate program goals, tracked below): G4 ratio-crop
      placement, G5 scope-truth pass, G6 publish path.
- Release: **v0.4.1** shipped 2026-09-25 — version bump (`pyproject` +
      `__about__`) + CHANGELOG `[0.4.1]`, tag + GitHub release
      (https://github.com/Dream-Pixels-Forge/brandly-cli/releases/tag/v0.4.1),
      `release.yml` green, PyPI verified (`brandly-cli==0.4.1`, sdist + wheel),
      CI green on `main` @ `9b702a3`.
- Global Python env repaired (incident recorded): `pip install --upgrade` hit
      WinError 32 — a live `brandly produce rebel` held `brandly.exe` — *after*
      pip had already renamed the old package aside (`~randly_cli`), leaving the
      global install half-removed. Repaired without touching the process:
      extracted the official `brandly_cli-0.4.1-py3-none-any.whl` into
      site-packages (byte-identical for pure wheels), removed pip's `~randly_cli*`
      remnants, verified `pip show` → 0.4.1, cmd-first import, and global
      `brandly --help`. The running produce (PID 25244) was never touched.

### Round 2/256 — Feature Implementation (Phase 3)
- [x] Created dev-notes/IMPLEMENTATION.md with full feature plan
- [x] Delegating subagents for Phase 3A features:
  - [x] Subagent #1: stitch (multi-shot video assembly) - 21 tests
  - [x] Subagent #2: export_platforms (platform-optimized exports) - 9 tests
  - [x] Subagent #3: thumbnails (AI-generated thumbnails) - 10 tests
- [x] Phase 3B features implemented:
  - [x] Subagent #4: voice-match/dubbing (multi-language) - 11 tests
  - [x] Subagent #5: beat-sync (music-reactive editing) - 7 tests
  - [x] Subagent #6: auto-direct (script-to-video) - 10 tests
  - [x] Subagent #7: trend research - 18 tests
- [x] Phase 3C features implemented:
  - [x] Subagent #8: analyzer (performance prediction) - 18 tests
  - [x] Subagent #9: templates (project configs) - 13 tests
  - [x] Subagent #10: batch (enhanced)
  - [x] Subagent #11: webhook (CI/CD integration) - 8 tests
- [x] Phase 3D features implemented:
  - [x] Subagent #12: share (cloud export) - 8 tests
  - [ ] Subagent #13: team (multi-user)
  - [ ] Subagent #14: plugin (extensibility)
- [x] Total tests: 303 passed
- [x] Ruff lint: clean
- [x] Python syntax: clean

## Blockers
- None

## Decisions Made
1. **Path resolution fix**: Added `root` parameter to utility functions instead of trying to detect ROOT env — cleaner API and explicit
2. **Skip Phase 1**: Project already exists with established architecture; brainstorm not needed
3. **Add SECURITY.md**: Even though risk is low, documenting the threat model is good practice
4. **Add SPEC.md**: Architecture was well-documented but a formal spec aids onboarding

## Next Steps
1. [x] Bump version to 0.2.0 in `pyproject.toml` and `__about__.py`
2. [x] Add pre-commit hooks (ruff + pytest)
3. [x] Consider adding a Makefile for common dev tasks
4. [x] Review whether SECURITY.md is needed (CLI has no auth beyond API keys)

### Round 4/256 — v0.3.26 release + G7 agentic-orchestration kickoff

- [x] Bumped version 0.3.25 → 0.3.26 (`__about__.py` + `pyproject.toml`, ci.yml parity check)
- [x] CHANGELOG 0.3.26 entry: G1 tool surface, G2 real director orchestration, G3 scene model + gate
- [x] Commit `a750d4e` pushed to main; tag `v0.3.26` pushed; GitHub release v0.3.26 published → `release.yml` → PyPI
- [x] **v0.3.26 is the rollback point for G7**: `git reset --hard v0.3.26` / `pip install brandly-cli==0.3.26`
- [x] Created `dev-notes/GOAL-AGENTIC-ORCHESTRATION.md` (G7: orchestrator + subagent contract layer; PR E/F/G; ships v0.4.0)
- [ ] NEXT: G7 PR E — TDD `phase_handoffs()` + `brandly plan --json` + agent_surface manifest entry

