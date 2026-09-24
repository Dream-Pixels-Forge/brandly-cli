# Pipeline Progress — brandly-cli

## Current State
- Project: brandly-cli
- Started: 2026-09-07
- Version: 0.2.0 → 0.3.0 (in progress)
- Current Phase: Phase 3 (Engineer) — Feature Implementation
- Status: in-progress (core features complete)
- Test Count: 303 passed
- Lint: 9 minor issues (non-blocking)

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
- [ ] **G2** Real director orchestration (`run --execute`, produce-backed phases, stub removal) — IN PROGRESS
  - [x] PR A: `brandly run <id> --execute [--until <phase>] [--yes]` drives
        `Director.run_pipeline` (resumable from `project.phases`); `run_phase`
        fails closed (worker error/exception → phase `failed`, `current_phase`
        frozen, pipeline stops, exit 1); fabricated stubs (`concept`/`asset`/
        `re_edit`/`publish`) report "not implemented" instead of fake success
        (TDD: 11 tests RED → GREEN; `tests/test_pipeline_orchestration.py`)
  - [x] PR B: `script` writes real `shots.json` (scene ids per G3); `asset`
        invokes the produce/shot_runner path
  - [ ] PR C: `re_edit` stitches; `validate` runs the G3 scene gate; `publish`
        calls export-platforms; E2E with mocked providers
  - [ ] PR D: `autodirector.auto_direct` removal/delegation; `brandly director`
        prints the orchestrator plan
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
