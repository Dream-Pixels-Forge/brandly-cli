# Pipeline Progress — brandly-cli

## Current State
- Project: brandly-cli
- Started: 2026-09-07
- Version: 0.10.2 (cut 2026-10-04; prior 0.10.1; #197 #208 #210)
- Current Phase: Phase 3 (Engineer) — Feature Implementation
- Status: in-progress (backlog closed; publish path shipped across all three F9 platforms)
- Test Count: 1294 passed (0 xfail/xpass)
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

### Round 7/256 — v0.5.0 release (G4 + G5 + G6 PR 1/3 shipped)

- [x] Bumped 0.4.1 → 0.5.0 (`pyproject.toml` + `__about__.py`; release.yml tag-parity gate)
- [x] CHANGELOG: three stacked `[Unreleased]` sections (G4, G5, G6) consolidated into `[0.5.0] — 2026-09-25`
- [x] Local gate stack green: ruff + mypy + import-linter + full pytest suite (806 passed); `python -m build` → clean sdist + wheel
- [x] Tag `v0.5.0` + GitHub release published → `release.yml` (OIDC trusted publishing) green → PyPI verified: 2 files uploaded 2026-09-25T19:52Z, `pip install brandly-cli==0.5.0` smoke-tested in a fresh venv (`brandly --version` → 0.5.0, `capabilities` shows the `publish_schedule` row)
- [x] v0.5.0 is the rollback point for G6 follow-ups: `pip install brandly-cli==0.5.0`
- NEXT: G6 PR 2/3 (live YouTube upload, credential-gated) and PR 3/3 (TikTok/IG adapters); issues #98 (brand kit) and #99 (metrics ingest) remain open

### Round 8/256 — v0.6.0 release (F9 closure: G7 brand kit + G8 metrics ingest)

Decision gates DEV-G7-001..003 + DEV-G8-001..003 all confirmed on
defaults; shipped as four TDD PRs behind one release, per
`dev-notes/GOAL-BRAND-KIT-METRICS.md` (PR #105 plan).

- [x] **G7 PR 1 (#106)** — `brand_kit.py` model (palette / claim allowlist /
  style lock / overlay spec, `.brandly/<project>/brand.json`, F2
  project-local) + `brandly brand init/verify/show` + prompt-layer lock
  (`apply_brand_lock`, conflicting styles raise `BrandLockConflictError`);
  capability row absent → partial
- [x] **G8 PR 1 (#107)** — `metrics.py` + `brandly metrics import/show`
  (versioned CSV/JSON → project-local snapshots) + `analyze`
  ingested-vs-heuristic source labelling (DEV-G8-002); capability row
  partial → supported
- [x] **G7 PR 2 (#108)** — gate claim-lock (off-allowlist on-screen text
  hard-fails `brandly gate --scene/--all-scenes`) + `export-platforms
  --brand` ffmpeg logo overlay (corner/safe-zone/opacity, fail-closed);
  e2e dry-run proof; capability row partial → **supported**
- [x] **G8 PR 2 (#109)** — `youtube_analytics.py` adapter
  (`reports:query`, credential-gated via `brandly config set
  youtube:analytics <token>`, dry-run-first, G6 pattern) writing through
  the shared `import_rows` core; TikTok/IG analytics stay planned
  (DEV-G8-003)
- [x] Local gate stack green: ruff clean, mypy `Success` (85 files),
  full pytest suite **857 passed / 0 failed** (up from 806 at v0.5.0)
- [x] Bumped 0.5.0 → 0.6.0 (`pyproject.toml` + `__about__.py`, tag-parity
  gate); CHANGELOG `[Unreleased]` consolidated into `[0.6.0] — 2026-09-25`
- [x] Tag `v0.6.0` + GitHub release → `release.yml` (OIDC trusted
  publishing) green → PyPI verified: `pip install brandly-cli==0.6.0` in a
  fresh venv (`brandly --version` → 0.6.0; `capabilities` shows
  `brand_kit` = supported and `metrics_ingest` = supported; `brand` +
  `metrics` command groups present)
- [x] Issues #98 + #99 closed with the capability-matrix link
- v0.6.0 is the rollback point for G6 follow-ups: `pip install
  brandly-cli==0.6.0` (previous: `0.5.0`)
- NEXT: G6 PR 2/3 live-upload follow-ups (YouTube live, TikTok/IG
  adapters) + TikTok/IG analytics adapters

### Round 9/256 — v0.6.0 skills documentation alignment (PR #110)

- [x] Documented the shipped v0.6.0 CLI surface in both video skills
  (docs-only; zero production code touched):
  - `skills/brandly-video-generation/SKILL.md`: `brand.json` + `metrics/`
    in the layout tree; G7/G8 key rules (three-layer brand enforcement,
    fail-closed; project-local metrics snapshots); two routing rows; new
    `## Brand Kit & Metrics (v0.6.0)` section (`brand init/verify/show`,
    gate claim-lock, `export-platforms --brand` overlay, `metrics
    import/show/ingest`, `analyze` ingested-vs-heuristic labelling);
    campaign example extended to 7 steps; brand/metrics troubleshooting
    subsection
  - `skills/brandly-film-director/SKILL.md`: description now covers
    brand-kit locks; 8-layer framework "Brand lock (v0.6.0)" callout
    (direct inside `palette/claims/style_lock`; `BrandLockConflict`);
    Template 2 brand rules; two checklist items; Pitfall 9 (off-brand
    frames and copy); workflow close-loop steps 11–12 (brand gate +
    metrics close-loop) with matching Next Steps
- [x] All CLI facts anchored to v0.6.0 source (`cmd/brand.py`,
  `cmd/gate.py`, `cmd/post.py`, `cmd/metrics.py`, `metrics.py`,
  `youtube_analytics.py`, `capabilities.py`); agentskills spec intact
  (name == folder, single-sentence trigger)
- [x] PR #110 (`chore/skills-v060`, commit `8372b41`) squash-merged to
  main as `a6047ad`; CI green (web-quality + quality matrix)
- NEXT: G6 PR 2/3 live-upload follow-ups (YouTube live, TikTok/IG
  adapters) + TikTok/IG analytics adapters

### Round 10/256 — v0.10.1 release (chore/test patch)

- [x] Bumped 0.10.0 → 0.10.1 in single source `src/brandly_cli/__about__.py` (hatch dynamic version drives pyproject); commit `858ef48` pushed to main; lightweight tag `v0.10.1` pushed
- [x] Ships PR #203 + #204 (myr-141505 i2v/t2v-fallback test hardening; agent-tools to_json re-export); no new runtime code → patch
- [x] `scripts/version_check.py` (plain + `--tag v0.10.1`) + `version_is_single_sourced` invariant green
- [x] GitHub Release v0.10.1 → `release.yml` (OIDC trusted publishing) green, incl. built-in "verify installable from PyPI" gate; PyPI `0.10.1` verified (wheel + sdist)
- [x] v0.10.1 is the rollback point: `pip install brandly-cli==0.10.1` (previous: `0.10.0`)
- NEXT: resolved — issue #205 fixed by PR #206 (squash `f0f9bb0` to main, #205 auto-closed)


### Round 10/256 — production-run hardening batch: issues #113–#125 closed, web monitor + review queue shipped

- [x] Merged all 13 open PRs (#128–#140) one at a time, each CI-green:
  - #128/#129/#130/#131 (fixes: duplicate shot ids fail closed, v2 web
    timeline resolver, `brandly mux`, polish trio)
  - #132/#133 (produce `--continue-on-fail`, `--dry-run` shot list)
  - #134 (v2 tree + plate discovery), #135 (SRT/VTT captions)
  - #136/#137 (gate scores in produce, video-quota accounting)
  - #138/#139/#140 (create spacing + `--park-after`, `brandly assemble`,
    in-flight ledger + `job-resume --sweep`)
- [x] Conflict resolutions recorded: #136/#138 rebased onto main and combined
  (`--continue-on-fail` + `--dry-run` + `--gate-threshold` + `--park-after`
  all wired into the produce runner); #138's stacked base retargeted to main
- [x] Integration fixes found by validation (each with a regression test):
  - #124's process-level create-spacing guard leaked 60s sleeps into
    unrelated tests → `tests/conftest.py` autouse reset (test_agnes_client
    back to ~2s)
  - #118's quota test was time-of-day dependent (red main on runs between
    00:00–00:30 UTC) → noon-UTC anchor (hotfix PR #141, main restored)
  - SPA template EOL drift failed the web-quality freshness gate →
    `web/index.html` normalized + `eol=lf` pinned (in #142)
- [x] Issue #126 shipped (PR #142): `web/monitor.py` per-shot matrix +
  gate scores + provider health + `/monitor` snapshot + `/monitor/tail` +
  ws `monitor_tail` watcher; ProductionMonitorPanel with copy-resume actions
- [x] Issue #127 shipped (PR #143): `web/review.py` review queue +
  approve/reject + contained media route; ReviewQueuePanel with
  stage/scene/gate-threshold filters; reject writes the standard review note
  and un-completes the shot in the progress log
- [x] #133's xfail converted to a real assertion (duplicate-id dry-run error)
- NEXT: v0.7.0 release cut (decision-gated) + #97 TikTok/IG publish/analytics


### Round 11/256 — F9 publish path closed (#97): TikTok + Instagram adapters, backlog CLEAR

- [x] Issue #97 shipped (PR #145, TDD 13 tests) on the same `Adapter` interface:
  - **TikTok** — direct-post init (`/v2/post/publish/video/init/`):
    FILE_UPLOAD chunking (byte size from the video, 64 MiB chunks,
    `total_chunk_count` splits bigger files), `SELF_ONLY` privacy default,
    caption folds title + description (TikTok's single caption field)
  - **Instagram** — Reels via the Graph API two-step container flow
    (`/me/media` create → `/me/media_publish`, container id reused); the
    Graph API cannot fetch local files, so a Reel needs a publicly
    reachable `--video-url` — fail-closed without one
  - Anti-drift held: dry-run renders the exact payload and never posts;
    live only behind a stored credential (`brandly config set <platform>
    <token>`); scheduling only where the platform supports it — YouTube
    `publishAt`, TikTok refuses `--schedule` (no scheduling in direct post)
- [x] Shared `_post_json` live executor (YouTube's duplicate block collapsed)
- [x] CLI: `--platform youtube|tiktok|instagram` + `--video-url`; payload
  validation surfaces as a clean error, not a traceback
- [x] Scope truth: capability row `publish_schedule` → `supported`; README
  roadmap line moved to the shipped features; DEV-G6-001 stamped with the
  shipped state
- [x] Full suite 976 passed (0 xfail/xpass); ruff + mypy + import-linter clean
- **Backlog status: 0 open issues, 0 open PRs** — the entire tracked backlog
  (#15–#127 + F9 #97) is closed
- NEXT: v0.7.0 release cut (decision-gated, manual publish approval)

### Round 12/256 — Studio shell shipped from the frozen Paper design (Increment A)

**Current Phase:** Phase 3 (Engineer) — web UI redesign · **Status:** Increment A green

- [x] Loaded `pipeline-orchestrator`; Phase 0 recon on the existing project
      (Phase 1 skipped — existing project), resumed at Phase 2.
- [x] Phase 2 governance: `dev-notes/DESIGN-STUDIO-SHELL.md` (frozen spec from
      Paper file `01M3VWT0PHVWKPN9JSECCES8T4`, page `p-3-0`) +
      `dev-notes/GOAL-WEB-UI-DESIGN.md` (scope, anti-drift constraints, gates).
- [x] **Anti-drift decisions recorded:**
      - Paper MCP was rate-limited (“Weekly MCP limit reached”) → the design was
        frozen into the spec doc from the authored spec instead of being guessed.
      - Screens 05 (Review Queue) / 06 (Agnes AI Synthesizer) have **no Paper
        design** (empty artboards) → declared **out of scope**, not invented.
      - No JS test runner introduced — the repo’s ratified convention (see
        `test_web_panels_wired.py`, issue #61) is Python source-contract tests
        + the `web-quality` CI job. Adding vitest would be new architecture.
      - No new API/data: Status Bar renders only store-backed values.
- [x] **TDD RED → GREEN:** `tests/test_web_studio_shell.py` written first
      (RED: 7 failed / 3 passed) → implemented → **10 passed**.
- [x] Fixed a latent defect: `--md-radius-sm/-md/-lg`, `--md-transition-fast`
      and `--md-font-body-md/code-inline/display-lg` were referenced by ~20
      components but **never defined**, so radii/fonts/transitions silently fell
      back to browser defaults. Now defined in `web/index.html` `:root`.
- [x] `Toolbar.tsx` (40px): breadcrumb `project › panel`, ⌘K search,
      undo/redo (disabled — no store support), Share (copies CLI cmd), help.
- [x] `StatusBar.tsx` (28px): phase pill, shots/clips, fps/aspect/selection,
      zoom/frame — all store-backed; gate score, credit budget and worker/RSS
      telemetry deliberately **omitted** (no data source → not fabricated).
- [x] `panelLabels.ts`: `PANEL_LABELS` + `PANEL_SHORTCUTS` single source of
      truth for nav labels, breadcrumb and shortcuts (also clears the
      `react/only-export-components` lint warning).
- [x] `SidebarNav.tsx`: telemetry block removed (→ Status Bar), footer
      `New Project` CTA + Docs/Shortcuts/CLI, per-row shortcut chips (P T A I R M Q G);
      `loading`/`error` boot contract preserved.
- [x] `Shell.css`: grid pinned to the frozen metrics — Header 52 / Toolbar 40 /
      Body / Status Bar 28, sidebar 248, main `padding:14` `gap:12`,
      `.panel-host` flex-fills so panels can use `height:100%`.
- Gates green: contract tests **54 passed** (studio shell + panels wired +
  shell boot + SPA bundle + security) · `npm run lint` **0 warnings / 0 errors**
  · `npm run build` (tsc -b + vite) emitted `src/brandly_cli/web/static/`.
- [x] **Increment B (Preview screen) — GREEN.** RED `tests/test_web_preview_rail.py`
      (4 failed / 1 passed) → implemented → **5 passed**.
  - [x] `ClipInspectorPanel.tsx` — 300px rail beside the viewport: properties
        (shot/scene/duration/aspect/style/grade/transition/quality), transition
        chips (`updateClip` — real action), prompt, Regenerate
        (`regenerateClip` — real). **Approve disabled** — the store has no
        review API, so it is *not* faked.
  - [x] `TransportControls` gained an `overlay` mode (absolute + scrim
        gradient) rendered **inside** the frame; the separate transport row was
        removed — it was in fact being rendered **twice** (once from `Shell.tsx`,
        once from `PreviewPanel.tsx`), a real defect this work caught.
  - [x] Prompt callout lifted `bottom: 8 → 54` so it clears the overlay.
  - [x] `Shell.css`: `.preview-workspace` + `.preview-stage-host` +
        `.clip-inspector` (fixed 300px).
- Gates green: web suites **79 passed** · `npm run lint` **0/0** ·
  `npm run build` (48 modules, 360.30 kB) refreshed `src/brandly_cli/web/static/`.
- **DEFERRED (recorded, not silently skipped):** the 3-track V2/V1/A1 timeline —
  `TimelinePanel.tsx` is dnd-kit driven and is a high-risk refactor, so it is
  scheduled as **Increment B2** rather than attempted inside the same pass.
- [x] **Increment C (Shot List bulk selection) — GREEN.** RED
      `tests/test_web_shotlist_select.py` (5 failed) → implemented → **5 passed**.
  - [x] `store.ts`: `selectedClipIds: string[]` + `toggleClipSelected` +
        `clearSelection`.
  - [x] `ShotListPanel.tsx`: a `role="checkbox"` button on every row
        (`stopPropagation` so selecting never jumps to Preview) and a
        contextual **Selection Bar** that appears only once something is
        selected, showing `{selectedClipIds.length} SELECTED`.
  - [x] Data honesty in the bulk bar: **Generate** → real `regenerateClip`;
        **Approve** disabled (no review API in the store — not faked);
        **Clear selection** → real.
- [x] **Increment D (Render + Monitor steppers) — GREEN.** RED
      `tests/test_web_steppers.py` (6 failed) → implemented → **6 passed**.
  - [x] `PipelineStepper.tsx` (Render): Plan locked → Rendering → Encode →
        Publish, derived from `exportDone` only — no invented per-stage progress.
  - [x] `PhaseStepper.tsx` (Monitor): the PRIDES chain rendered as pipeline
        context + the project's **real** `current_phase` as a pill. `current_phase`
        has no guaranteed PRIDES mapping, so the chain is **not** marked with a
        fabricated "current" step.
  - [x] `RenderDispatchPanel.tsx`: settings column constrained to **440px**
        (design §7, artboard 03) so the controls stop stretching full-bleed.
  - [x] Caught by the build gate: the steppers use default exports — named
        imports failed `tsc -b` (TS2614) and were corrected.
- Gates green: contract suites **33 passed** · `npm run lint` **0/0** ·
  `npm run build` (50 modules, 366.55 kB) refreshed `src/brandly_cli/web/static/`.
- **Still deferred:** the 3-track V2/V1/A1 timeline (Increment B2, high-risk
  dnd-kit refactor) and the Shot Inspector tabs (C2). Screens 05/06 blocked on
  their Paper design (empty artboards — design pass pending).

#### Git delivery (PRIDES taxonomy)

- [x] Branches had **diverged** (main +2 docs/version commits, HEAD +2 agnes
      fixes) — verified **no overlap** with any file touched before switching,
      so nothing was clobbered.
- [x] `feature/studio-shell-redesign` created **from `main`** (correct taxonomy:
      `feature` branches from `main`, merges into `main`).
- [x] Committed `10c3135` — 28 files, +1643/−102 (pre-existing untracked
      `region_dump.txt` deliberately excluded).
- [x] Pushed to `origin` with upstream tracking.
- [x] **PR #185 MERGED** — <https://github.com/Dream-Pixels-Forge/brandly-cli/pull/185>
      merge commit `ed54983` (2026-10-01T20:58:45Z). Pre-merge verification:
      all 4 CI checks green, `mergeStateStatus: CLEAN`, **zero** comments /
      reviews / warnings. `origin/main` carries both feature commits and every
      new component + test file. Local `main` is checked out in another
      worktree, so the merge was verified by ref (`origin/main`) — that
      worktree was left untouched.

#### Round 12 continued — Increments C2 + B2

- [x] CI on PR #185: **all four checks pass** (quality 3.10/3.11/3.12 +
      `web-quality`). Not merged — review required.
- [x] **Increment C2 (Shot Inspector tabs) — GREEN.** RED
      `tests/test_web_inspector_tabs.py` (4 failed) → implemented → **4 passed**.
  - [x] `ClipInspectorPanel.tsx`: an interactive tab row (`role="tablist"` /
        `role="tab"` + `aria-selected`) with **Overview / Prompt / Gate**.
  - [x] Gate tab is data-honest: it shows the clip's real `quality_status` and
        **discloses that no gate score exists on the clip record** (scores come
        from the Production Monitor / `brandly gate`) — nothing invented.
  - [x] `Shell.tsx`: the Shot List now sits in a `shot-workspace` row with the
        Clip Inspector rail, so artboard 02 matches the design.
- [x] **Increment B2 (3-track timeline) — resolved by inspection, no code change.**
      `TimelinePanel.tsx` is **already 3-track**: V1 video track + A1 MiniMax VO +
      A2 BGM 124BPM + ruler, with dnd-kit reordering, trim and playhead drag.
      The design's remaining delta (a V2 overlay track) would need an
      overlay-track data model that does not exist in the store or API →
      **out of scope under the data-honesty rule**, not fabricated.
- Gates green: contract suites **31 passed** · `npm run lint` **0/0** ·
  `npm run build` (50 modules, 368.16 kB) refreshed `src/brandly_cli/web/static/`.
- NEXT: full-suite run in flight; commit + push to PR #185; screens 05/06
  blocked on their Paper design.

#### Round 12 continued — issue #184 fixed (init root hijack)

- [x] **Issue #184 fixed — `init` now creates the project in the cwd.**
      `gh issue view 184`: `_get_root` walked UP from cwd and hijacked the root
      to the first ancestor with a `.brandly` store (the user's home, where the
      global store lives), so `init` from a subfolder created the project in the
      ancestor's store and the working directory got nothing.
  - [x] `cli.py::_get_root(ctx, *, create=False)` — with `create=True` the
        walk-up is **skipped** and the root is `cwd` (the `.brandly` marker only
        matters when *reading* an existing project, never when creating).
  - [x] `cli.py::_warn_if_ancestor_store(cwd)` — when `init` skips a detected
        ancestor store it tells the user and hints at `--root` (issue option 3).
  - [x] `cmd/production.py::init` → `_get_root(ctx, create=True)`.
  - [x] **Deliberately unchanged (surgical):** `web/server.py::_discover_root`
        (the server only ever *reads* an existing project, so its walk-up is
        correct); explicit `--root`/`$ROOT` still win; read/resume commands keep
        the walk-up.
  - [x] **TDD RED → GREEN:** `tests/test_issue_184_init_root.py` written first
        (8 failed / 1 passed) → implemented → **9 passed**. Two initial failures
        were environment-dependent tests (tmp_path sits under the real home, so
        the walk-up reached it) — made hermetic by nesting past the 10-level
        walk-up limit.
  - [x] **Verified on the real machine (e2e):** `init` with no `--root` from
        `%TEMP%\brandly-e2e-184` created `.brandly\smoke` **in the cwd** and
        `brandly list` finds it; the ancestor-store hint prints with the `--root`
        pointer. Temp dirs cleaned up afterwards.
- Gates green: existing CLI tests **49 passed** · ruff clean ·
  **mypy clean (92 source files)** · full suite **1164 passed, 0 failures**.
- [x] **PR #187 MERGED** — <https://github.com/Dream-Pixels-Forge/brandly-cli/pull/187>
      merge commit `1d5d372` (2026-10-01T22:53:20Z). Pre-merge verification: all
      4 CI checks green (quality 3.10/3.11/3.12 + web-quality), `mergeStateStatus:
      CLEAN`, zero comments/reviews/warnings. **Issue #184 auto-CLOSED** by
      `Fixes #184`. Verified on `origin/main` by ref (local `main` lives in
      another worktree — left untouched).

#### Session ledger — PRIDES end-of-task state

- [x] Tests pass — full suite **1164 passed, 0 failures** (issue #184 branch:
      1007 + 9 regression tests; CI green on 3.10/3.11/3.12)
- [x] Committed on the correct taxonomy branches
      (`feature/studio-shell-redesign`, `chore/process-discipline`,
      `bug/init-root-hijack-184`) — each branched from `main` after a
      divergence + overlap check
- [x] Pushed to origin
- [x] PRs opened **and merged after review**: #185 (studio shell),
      #186 (process discipline), #187 (issue #184)
- [x] Process discipline persisted as strict mandatory:
      `~/.agents/AGENTS.md` §10 (workspace-wide), `AGENTS.md` (repo root),
      `dev-notes/CONVENTIONS.md` (full discipline + deferrals ledger)
- [ ] **Blocked on the Paper design:** screens 05 (Review Queue) and 06
      (Agnes AI Synthesizer) — Paper artboards `1T8-0` / `1T9-0` are empty and
      the Paper MCP is rate-limited ("Weekly MCP limit reached. It resets
      tomorrow"). The scheduled design run fires tomorrow 10:00 +01:00
      (`sched_34431552-3355-416e-a781-9f463c4114be`); the web-UI PNG export to
      `assets/` is folded into that run (Paper export is the only way to
      produce it, and `assets/` currently holds only `banner.png`).
- [ ] Deferred (data honesty / no design): V2 overlay track (B2).




### Round 12/256 — Agnes 503 hardening batch: issues #148–#152 closed (PR #153)

- [x] Filed #148–#152 from live probes against `apihub.agnes-ai.com/v1`
  (bogus model → 503 `model_not_found`; bad `size=480P` → 400 with
  top-level `code`; `GET /v1/models` → 200 catalog)
- [x] TDD RED → GREEN on `fix/agnes-503-hardening`: 39 new tests
  (`tests/test_issue_148-151.py` + #152 case in `test_issues_19_24.py`),
  RED confirmed (37 failed / 1 intentional guard), then GREEN
- [x] PR #153 merged (merge commit `82dd367`, CI `quality` 3.10/3.11/3.12 +
  `web-quality` all green); the 5 issues auto-closed:
  - **#148** `_parse_error_body` + `_classify_status` +
    `GET /v1/models` disambiguation (300s cache, fail-open); permanent
    messages carry code, request id, available models
  - **#149** no sleep after the final attempt; `_print_exhausted`
    reports attempts/elapsed/body/request id; "will retry" promises
    removed from image/create/status/chat; park line is advice-only
  - **#150** all docs-`retry later` 5xx retried client-side;
    `poll_video` survives transient 5xx; monotonic 10/20/40/60 backoff
  - **#151** create budget 6 → 3 spaced attempts, 60s spacing intact
  - **#152** batch-variants `--wait` forwards `model_name`
- [x] Live side-effect-free probes verified both paths (permanent with
  catalog hint + request id; parsed 400 unchanged) before merge
- [x] Full suite 1015 passed; ruff + mypy clean
- [x] Filed #154 from probe fallout: Rich legacy-Windows cp1252 path
  crashes on `✗`/`⚠` glyphs (33 pre-existing usages; `PYTHONUTF8=1`
  workaround) — pre-existing, out of this batch's scope
- NEXT: #154 console-encoding fix; v0.7.1/publish decision


### Round 13/256 — Agnes doc-distillation batch: issues #154 + #156–#161 closed (PRs #162–#168)

- [x] Diffed the 3 vault Agnes docs (`raw/Agnes Docs/`, clipped
  2026-09-29) against the code → findings G1–G6 filed as #156–#161,
  all `status:ready`; #154 (Round 12 fallout) joined the batch
- [x] Six fixes merged one at a time, each branch cut from fresh
  `origin/main`, TDD RED first, CI (`quality` 3.10/3.11/3.12 +
  `web-quality`) green, squash-merged, issue auto-closed:
  - **#156** (PR #162) `infer_video_mode` takes `reference_audios`;
    reference degrades to text mode only when images AND audios are
    empty — pure-audio inputs stay in reference mode (4 new tests)
  - **#160** (PR #163) `_validate_flash_create` client-side pre-validation
    for Flash video: size in {21:9,16:9,4:3,1:1,3:4,9:16}, images ≤5,
    audios ≤3, no `videos` (5 new tests)
  - **#157** (PR #164) three stale `agnes-image-2.1-flash` defaults →
    `DEFAULT_AGNES_IMAGE_MODEL` (image option+help, production
    `generate_image`, sync provider id; rg-verified: only catalog
    entries remain)
  - **#161** (PR #165) `AGNES_IMAGE_RATIOS` (8 supported ratios) +
    `click.Choice` on `brandly image`/`brandly reference` `--ratio` —
    unsupported values rejected at parse time; ffmpeg-side crop ratios
    untouched (3 new tests)
  - **#158** (PR #166) reference prompts bind media via `<Picture N>`/
    `<Audio N>` tokens built from actual inputs (1-based, array order;
    images-only / audios-only / mixed), replacing the unconditional
    image-only prose hint (5 new tests)
  - **#159** (PR #167) `agnes-3.0-flash` added to the text-model catalog
    (512K ctx, 65.5K output, $0); live smoke `agnes-chat --model
    agnes-3.0-flash` answered, and a tool-call probe returned a
    well-formed `tool_calls` entry — tool calling VERIFIED; default
    stays 2.5-flash (flip = separate decision) (3 new tests)
  - **#154** (PR #168) `ensure_utf8_output()` at package import
    reconfigures stdout/stderr to UTF-8 + `errors=replace`, replacing
    the v0.3.13 `cli()`-only, win32-only block that library paths
    bypassed; issue repro (`✗` on cp1252 stdout) now prints, exit 0
    (3 new tests)
- [x] 23 new tests total (RED confirmed before each GREEN); full suite
  **1038 passed** (from 1015); ruff + mypy clean
- **Backlog status: 0 open issues, 0 open PRs**
- NEXT: v0.7.1 release cut / publish decision (decision-gated)

### Round 14/256 - Agnes text-model enhancement batch: issues #170-#171 closed (PRs #175-#176)

- [x] Filed the post-#159 backlog (tool calling verified on
  `agnes-3.0-flash`): #170 (opt-in LLM prompt enhancement), #171 (gate
  `--judge-model` + multi-frame judging), #172 (storyboard-from-brief),
  #173 (`gate report --explain`), #174 (prompt drift). #170/#171 marked
  `status:ready` (design clear, cheapest wins); #172-#174 parked in the
  backlog pending triage
- [x] **#170** (PR #175) `--llm-enhance` + `--llm-model` on `brandly
  image`/`brandly video`: new `prompt_enhance.llm_enhance_prompt`
  rewrites the final prompt through an Agnes text model (cinematography
  expansion; `<Picture N>`/`<Audio N>` binding tokens preserved);
  fail-open on API error / malformed reply / lost binding token falls
  back to the deterministic prompt (19 new tests)
- [x] **#171** (PR #176) gate judge selection + multi-frame judging:
  `--judge-model` threads into `chat_completion(model=...)` (default
  unchanged); `--judge-frames 1..8` validated at parse time; videos with
  N>1 extract evenly spaced frames (`_extra_video_frames`/`_frame_at`),
  send them labeled in ONE call (`_run_vision_check_multi` +
  `_VISION_SYSTEM_MULTI` cross-frame consistency block) and aggregate
  worst-case (`_aggregate_multi_verdict`) into the single-verdict
  schema; single-frame stays the default and the fallback; `produce`
  gate untouched (`use_ai=False` - judge wiring there would be dead)
  (19 new tests)
- [x] Full suite **1076 passed** (from 1038); ruff + mypy clean
- **Backlog status: 0 open issues, 0 open PRs** (#172-#174 parked)
- NEXT: #172-#174 triage (storyboard-from-brief needs a design pass) /
  v0.7.1 release cut (decision-gated)

### Round 15/256 - Gate explain, prompt drift, storyboard from brief: issues #172-#174 closed (PRs #178-#180)

- [x] Triaged the parked #172-#174 trio: translated two subcommand
  proposals onto the actual command shapes (no `gate` subcommands
  exist): `gate drift` -> `brandly gate --explain` (#173),
  `gate report --explain`/drift -> top-level `brandly gate-drift` (#174)
- [x] **#173** (PR #178) `brandly gate --explain`: after the standard
  report, ONE extra text-model call diagnoses every failure/warning
  (element mode, `_EXPLAIN_SYSTEM`, shot prompt + progress context) and
  prints per-issue explanation, suggested fix and copy-pasteable
  commands; read-only, fail-open (invalid JSON / API error degrade to a
  note), zero file writes; `--json` gains `explain`/`explain_error`
  keys (10 new tests)
- [x] **#174** (PR #179) `brandly gate-drift <project>`: pre-generation
  cross-shot audit - all shot prompts in ONE text-model call
  (`_DRIFT_SYSTEM`; dimensions character|lighting|style|aspect|voice),
  drifts table with evidence/severity/suggested fix, `-o json`,
  `--strict` exits 1 on high severity, otherwise 0; exit 2 on invalid
  project id / missing or empty shots.json / API failure / malformed
  response (with response tail) (10 new tests)
- [x] **#172** (PR #180) `brandly storyboard --from-brief "<brief>"`
  (+ `--force`, `--brief-model`, `--style`, `--aspect`, `--duration`):
  one text-model call (default `agnes-2.5-flash`) -> validated shot list
  written to `--shots` -> stop before keyframes (no credits);
  `_validate_generated_shots` fail-closed on malformed JSON (response
  tail printed), non-canonical/duplicate ids (#113), missing prompts,
  durations outside 1-30 -> exit 2, NOTHING written; existing target
  refused without `--force` (exit 1, before any API call); flag absent
  = old behavior byte-identical (13 new tests)
- [x] Full suite **1109 passed** (from 1076); ruff + mypy clean
- **Backlog status: 0 open issues, 0 open PRs**
- NEXT: v0.8.0 release cut (decided 2026-09-29: minor bump - three
  feature batches since 0.7.0) / publish via tag -> release.yml -> PyPI

### Round 16/256 - Brandly clip-chain prompt grammar (PR #183)
- Translated cuts-language prompts to brandly language: a clip is ONE
  unbroken take; joins happen in post (`brandly stitch`) and are never
  written into a model-facing prompt
- **ShotChain** (`video_prompts.py`): `carry_over` line ("Carry over
  across all N clips: …"), per-clip `ends_on` ("Ends on …") + `handoff`
  ("Clip N-1→N handoff: …") replacing the old `--- CUT TO ---` tokens;
  new `clip_prompt(index)` = self-contained per-clip prompt with a
  `[CONTINUITY] Same … . Continuity from Clip N-1.` suffix on clips 2..N;
  `transition` kept as assembly metadata only (never emitted)
- **Structured prompts**: 3 new clip-chain layers — `performance` /
  `physics` / `locks` → `[PERFORMANCE]` / `[PHYSICS]` / `[POSITIVE LOCKS]`
  (unknown keys still fail loudly; the 8 base layers unchanged)
- **build_video_prompt**: master context gains a FORMAT MODE line —
  "Mode: N unbroken takes, Xs total — the chain is joined in post; a
  join never happens inside a generation."
- **build_enhanced_video_prompt**: `reference_notes` param →
  `[REFERENCE NOTES]` section with per-reference "defines / Do not use"
  exclusions; now exposed on the CLI as repeatable
  `brandly video --reference-note "REF[:DEFINES[:EXCLUDE]]"` (4 new
  tests)
- **Skill**: new "Shot-List Chain — Cut Scenes in Brandly Language"
  section in `brandly-continuous-action-film` (golden rule, brief
  structure, per-clip prompt shape, produce→gate→stitch loop)
- Doc sweep: stale "8-layer" descriptions fixed in `video_prompts.py` /
  `shot_runner.py` (historical CHANGELOG/dev-notes entries untouched)
- TDD (RED→GREEN): 15 new tests written first (11 in #183, 4 for the
  flag), 11 confirmed failing before implementation
- Full suite **1124 passed** on `feature/clip-chain-prompt-grammar`
  (1109 on main + 15 new); ruff + mypy clean
- **Backlog status: PR #183 open, awaiting review** / follow-up still
  open: CLI command emitting the full human-readable scene brief from a
  ShotChain (deferred — the skill + structured `produce` path already
  cover it; reassess before shipping)

### Round 17/256 - brandly-cli v0.9.0 released (PR #189)
- [x] Cut v0.9.0 (first release since 0.8.0, from #189 / c921c2c):
  bundles the Studio web shell (#185), DevShell (#186), video-prompt
  docs (#188) and the release increment itself (#189)
- [x] #189 increment: live Studio web UI screenshot
  (`assets/studio-preview.png`, headless Chromium, generated by
  `scripts/make_studio_preview.py`) shown in the README + new "Demos"
  section (Studio + 7 AI tools)
- [x] Version 0.8.0 -> 0.9.0 in `pyproject.toml` + `__about__.py`
- [x] Published via the repo's OIDC `release.yml`: tag `v0.9.0` ->
  GitHub release -> PyPI 0.9.0 (whl + sdist; installability verified)
- Docs-ledger update only this round; no code or tests
- NEXT: release path clear (v0.9.0 shipped); next increment TBD

### Round 18/256 - auto-ref scoping + retry backoff (#191/#192) and v2 media/export layout (#117)
- [x] #191/#192: per-shot auto-reference scoping + exponential retry backoff in
  the produce runner (TDD: tests/test_auto_ref_scoping.py, 14 tests) -> PR #193
- [x] #117 (cont.): move media + export under the v2 pre-production/production
  roots (layout.py + generation/production/publish/post + web export route; new
  tests/test_v2_media_layout.py) -> PR #194
- Decision: the #117 layout work first landed on PR #193 by accident. Split it
  onto its own branch/PR (fix/issue-117-v2-media-export / #194) so #193 stays
  focused on #191/#192. Verified the layout commit cherry-picks cleanly onto
  current main and is independent of the auto-refs commit.
- Note: the older fix/issue-117-v2-tree branch's init/plate-discovery commit is
  already in main (0-line diff on layout.py + test_issue_117.py) — that branch
  is superseded and needs no separate PR.
- Gates on the #117 branch (#194): full suite 1179 passed, ruff clean.
- Gates on #193: test_auto_ref_scoping.py 14 passed; PR mergeable.
- NEXT: PR #193 (auto-refs) + PR #194 (#117 layout) pending review/CI, then merge.

### Round 19/256 - shot-side reference enforcement + shot-list reference pre-flight (#195)
- [x] Honor `wardrobe`/`hq/` layout on the shot side, cap each shot's references
  to the model's 5-image limit, and never hard-fail `brandly video` on an
  over-limit payload (`shot_runner.py` + `cmd/generation.py` +
  `tests/test_shot_references.py`, commit 7b48639).
- [x] `brandly produce --check` pre-flight: new `shot_runner.check_shot_references`
  reports EVERY unresolvable shot reference (per shot/act/scene) in one pass
  instead of aborting on the first miss; non-check `produce` fails fast with the
  same aggregate (fixes #195). TDD: `tests/test_shot_references_check.py` (10 tests).
- [x] Refactored `flatten_shots` to reuse the shared `_entry_is_path` helper so the
  pre-flight check and the runner can never disagree about path-vs-stem.
- Opened #196 (produce auto-ref scoping — cross-ref'd to in-flight PR #193 /
  #191/#192) and #197 (`resolve_plate` vs `discover_project_plates` asymmetry).
- Gates: full suite 1214 passed; ruff clean (src/ + tests/).
- Status: local commit on feature/hq-references-wardrobe-screenplay; push/PR
  pending review sign-off.

### Round 20/256 - reference plate double-extension fix (e.g. `Hunter.png.png`)
- [x] Root cause: the `brandly reference` command renamed the saved plate to
  `layout.build_sheet_filename(...)`, which already embeds the file extension,
  then appended `ext` a second time → `char_Hunter_<ts>.png.png` (doubled `.png`).
- [x] Fix (`cmd/generation.py`): pass the real (`saved.suffix`) extension into
  `build_sheet_filename` and stop appending a second one. The plate now carries a
  single extension, and a `.jpg` artifact keeps its `.jpg` (previously `.png.jpg`).
  TDD: `tests/test_reference.py::test_reference_plate_has_single_extension`
  (RED observed on `...png.png`, then GREEN after the fix).
- [x] Gates: `tests/test_reference.py` 20/20; full suite 1215 passed / 0 failed;
  ruff clean (src/ + tests/).
- [x] Also fixed the red `tests/test_architecture_contracts.py::test_lint_imports_exits_zero_on_repo_root`:
  import-linter 2.15's default display path nests a `rich.Progress` over a `rich.Live`
  on the same console; rich >= 13.9 raises `LiveError: Only one live display may be
  active at once` *before* any contract is evaluated, forcing exit 1 even when all
  contracts are kept. Confirmed in isolation with a minimal repro — the collision only
  fires when the Progress is enabled; import-linter's `verbose=True` path disables it,
  so the check runs cleanly and reports "1 kept, 0 broken" -> exit 0. The gate now calls
  `lint_imports(..., verbose=True)` (display-only change; contract evaluation and its
  exit-code semantics are unchanged).
- Status: board clean (all gates green); pushing + opening PR for issue #195.

### Round 21/256 - Design: populated the two empty Studio screens (05 Review Queue, 06 Agnes AI Synthesizer)
- [x] Paper file `01M3VWT0PHVWKPN9JSECCES8T4` (page `p-3-0`): built out
  artboards `05 · Review Queue` (`1T8-0`) and `06 · Agnes AI Synthesizer`
  (`1T9-0`), the only two frames that were empty (0 children).
- [x] Reused the frozen shell (Header 52 / Toolbar 40 / Body[Sidebar 248 +
  Main] / Status Bar 28) by cloning artboard-01's shell nodes verbatim —
  exact MD3/`--studio-*` tokens, Space Mono + Hanken Grotesk, SVG icons.
  No new token namespace (spec §3). Per-screen deltas: toolbar breadcrumb
  label + active sidebar nav row + Main content only.
- [x] **05 delta:** status-filter segmented control (All/Awaiting/Passed/
  Flagged) + 8-row item list (thumbnail, provider line, G1–G3 gate bar,
  cost, status pill, approve/reject) + 300px review-detail rail (prompt,
  gate checklist, approve/reject) + summary footer.
- [x] **06 delta:** Agnes generation console (prompt box, style-preset
  chips, aspect/fit/seed params, credit-budget bar, Synthesize/Queue
  actions) paired with a 2×2 results grid (one selected variant) +
  run-summary footer.
- [x] Verified each screen with full-frame + region screenshots (spacing,
  hierarchy, contrast, alignment, artboard fit).
- [ ] Code: SPA contract tests (`tests/test_web_*.py`, RED first) for the
  two new panels are the next increment — OUT of scope for this design
  pass (no JS test runner in CI; see issue #61). 05/06 remain
  design-only until that contract exists.

### Round 22/256 - Design: split the Preview Player into a Timeline Sequencer (01) + a clean Preview Player (07)
- [x] Reframed the original `01 · Preview Player` as `01 · Timeline
  Sequencer` (`8R-0`): the screen keeps its timeline-heavy editing
  surface (transport overlay + 300px Clip Inspector rail + 3-track
  V2/V1/A1 timeline). The artboard name, the toolbar breadcrumb, and the
  active sidebar nav row all moved from “Preview Player” to “Timeline
  Sequencer” (row background / left accent bar / label weight+colour /
  icon strokes flipped on the `--studio-*` tokens — no new namespace).
- [x] Created a new `07 · Preview Player` (`2NA-0`) — a dedicated,
  **clean** playback surface with **no timeline and no Clip Inspector**:
  a large centered 16:9 stage reusing the exact transport overlay
  (play/pause · prev/next · scrubber · time · volume · fullscreen) + a
  slim preview control strip (shot name + PREVIEW chip + codec/fps/
  duration · Loop toggle · “Open in Timeline” primary action). Built by
  cloning the frozen shell from artboard-01, deleting the cloned
  `Timeline` + `Clip Inspector` nodes, reflowing the `Viewport Card` to
  center (852×534), and adding the control strip. Active nav = the
  “Preview Player” row.
- [x] The shared sidebar already carries both “Preview Player” and
  “Timeline Sequencer” nav items, so both screens are navigable and the
  nav stays consistent across the set.
- [x] Exported both as 2× PNGs to `C:\Users\Patrick\Downloads`:
  `01 · Timeline Sequencer@2x.png` + `07 · Preview Player@2x.png`.
- [ ] Code: SPA contract tests (`tests/test_web_*.py`, RED first) for the
  clean player + the sequencer reframe are the next increment — OUT of
  scope for this design pass (no JS test runner in CI; see issue #61).
- [x] Verified screens 05/06 sidebars this session: they already carry
  the **identical 9-node WORKSPACE nav** as 01–04/07 (a `WORKSPACE`
  section header + 8 items: `Preview Player`, `Timeline Sequencer`,
  `Asset Manifest` [8], `Props Inspector`, `Render Queue`,
  `Production Monitor`, `Review Queue` [3], `Agnes AI Synthesizer`),
  with the correct per-screen active row (05 → `Review Queue`, 06 →
  `Agnes AI`). Confirmed via the nav JSX + layer names
  (`Nav Review (active)` / `Nav Agnes AI (active)`) + 2× sidebar
  screenshots. An earlier note that 05/06 used a short 5-item nav was a
  mis-observation — **no reconciliation is needed**.

### Round 23/256 - Code: made the Studio shell panels production-ready (data-driven, no mocks)
- [x] **Reframed scope:** audited all 10 shell panels; **9 of 10 were already
  production-ready** (real store data, honest empty states, no fabricated
  telemetry). Only two carried mock data and needed de-mocking:
  - `Agnes AI Synthesizer` — was a `ShotListPanel` stand-in mapped to `agnes_ai`
  - `AudioMixer` — simulated the master VU meter via `Math.random` + `setInterval`
- [x] **New `web/src/components/panels/AgnesPanel.tsx`** implementing the frozen
  06-delta (DESIGN-STUDIO-SHELL §6 / Round 21): generation console (prompt,
  style-preset chips, aspect/fit/seed, credit-budget bar, Synthesize/Queue)
  paired with a 2×2 results grid (one selected variant) + run-summary footer.
  All state from `useAppStore` (clip / media / status / ws events); un-generated
  variants labelled "not generated"; credit bar stays at 0 with an explicit
  "no credit data — not wired" note; "Queue" is `disabled` with an honest
  `title`. No fabricated telemetry.
- [x] Wired `web/src/Shell.tsx`: `agnes_ai` now maps to `AgnesPanel` (import
  added; previously a `ShotListPanel` stand-in).
- [x] **AudioMixer de-mock:** removed the `Math.random`/`setInterval` VU loop —
  the master meter now renders an honest flat/idle state (null peak → "—")
  under a "No live metering — idle" label. The "Audition Voice" no-op
  (`updateClip` write that discarded the result) is now a `disabled` button with
  `title="No audio audition endpoint yet"`. Dropped the now-dead store coupling
  (`clip` / `selectedClipId` / `timeline` + the `useAppStore` + `Clip` imports).
- [x] **TDD RED → GREEN** via Python source-contract tests (no JS runner in CI;
  issue #61):
  - new `tests/test_web_agnes_panel.py` (wiring + data-honesty, 8 tests)
  - new `tests/test_web_audio_honesty.py` (no sim, honest VU label, no no-op
    audition, honest title, 4 tests)
  - `tests/test_web_panels_wired.py` now pins `agnes_ai → AgnesPanel`
- [x] **Gates all green:** frontend `oxlint` 0 warnings / 0 errors;
  `tsc -b && vite build` clean (bundle `index-CpI8wkTk.js` regenerated +
  committed); full suite **1244 passed**; `ruff` clean. Preview asset
  `assets/studio-preview.png` re-verified (PNG 1440×900, 58 KB; referenced by
  `tests/test_web_studio_preview.py`, not hard-coded in panels).
- [ ] Push + open PR for this increment (critical step — needs review; AGENTS §7/§8).




### Round 24/256 - Bug: aligned shot-side plate resolution with auto-ref discovery (issue #197)
- [x] RED first: `tests/test_issue_197.py` (7 cases) — 5 failed on main with
  `FileNotFoundError` (general / vehicle / nested / legacy / parity), 2
  guards (hq never resolves, missing stem still raises) green before and
  after.
- [x] Fix: `shot_runner.resolve_plate` gains a last-resort scoped `rglob`
  over both discovery bases (`images_dir` + the derived legacy
  `.brandly/<id>/images/` tree via `layout.project_dir`), suffix order
  preserved, skipping any `hq/` segment. `IMAGE_CATEGORIES` has 11 folders
  vs 4 `REF_CATEGORIES`, so plates in general/vehicle/mecha/animal/plant/
  keyframe/storyboard were auto-injected by `brandly video` yet raised
  `FileNotFoundError` when a shot list named them by bare stem (the
  split-brain).
- [x] GREEN: 81 passed (new + test_shot_references + test_shot_references_check
  + test_shot_runner); full suite 1285 passed (was 1278); ruff clean;
  mypy clean (92 files); version-check OK (0.10.1); web/static untouched.
- [x] PR #207 (`bug/align-plate-resolution`, commit `10bda38`) squash-merged
  to main; #197 auto-closed.
- NEXT: #196 (produce auto-ref scoping — needs a product decision) + #192
  (Agnes 503: backoff / queue-status / clearer error handling); #191 closed
  as a dup of #192.

### Round 25/256 - Bug: discover_project_plates skips nested hq/ segments (issue #208)
- [x] RED first: `tests/test_issue_208.py` (5 cases) — 4 failed on main: a
  nested master (`character/hq/x.jpg`) was discovered, auto-injected by
  `brandly video`, found in the legacy tree, and even re-split by
  `optimize_references` (writing a small JPG inside `character/hq/`). 1
  guard (top-level master still skipped) green before and after.
- [x] Fix: the top-level-only guard `rel.parts[0] == HQ_DIRNAME` became
  `HQ_DIRNAME in rel.parts` — any `hq/` segment under either scanned base
  (v2 root + legacy `.brandly/<id>/images/`) is skipped, matching the
  documented contract and the shot-side resolver's rule (#117, #207).
- [x] GREEN: 33 passed (new + test_layout + test_hq_references); full suite
  1290 passed (was 1285); ruff clean; mypy clean (92 files); version-check
  OK (0.10.1); web/static untouched.
- [x] PR #209 (`bug/discover-plates-nested-hq`, commit `f5d33c9`) squash-merged
  to main; #208 auto-closed.
- NEXT: #196 (produce auto-ref scoping — needs a product decision) + #192
  (Agnes 503: backoff / queue-status / clearer error handling).

### Round 26/256 - Bug: ensure_hq_split skips nested hq/ segments (issue #210)
- [x] RED first: `tests/test_issue_210.py` (4 cases) — the direct-call path
  re-split a nested master (`character/hq/x.png`): the master duplicated to
  the top-level `hq/character/` and a small JPG written *inside*
  `character/hq/`, violating the documented "already lives under hq/" no-op.
  3 guards (nested-in-legacy-tree, top-level hq, category-root split) green
  before and after.
- [x] Fix: `rel.parts[0] == layout.HQ_DIRNAME` became
  `layout.HQ_DIRNAME in rel.parts` — the same one-line shape as #208 on the
  walker side. #208 already guarded the walked path (`optimize_references`
  -> `discover_project_plates`); this pins the direct path
  (`cmd/generation.py` + public callers) to the same contract.
- [x] GREEN: 32 passed (new + test_hq_references + test_layout); full suite
  1294 passed (was 1290); ruff clean; mypy clean (92 files); version-check
  OK (0.10.1); web/static untouched.
- [x] PR #211 (`bug/hq-split-nested-guard`, commit `45775b2`) squash-merged
  to main; #210 auto-closed.
- NEXT: #196 (produce auto-ref scoping — needs a product decision) + #192
  (Agnes 503: backoff / queue-status / clearer error handling).

### Round 27/256 - v0.10.2 release (patch: reference plate resolution + nested hq guards)
- [x] Bumped 0.10.1 -> 0.10.2 in single source `src/brandly_cli/__about__.py`
  (hatch dynamic version drives pyproject); commit `42f7716` pushed to main;
  lightweight tag `v0.10.2` pushed; CHANGELOG.md gained the 0.10.2 entry
  (0.10.0/0.10.1 were never logged — backfill noted as a follow-up).
- [x] Ships PR #207 + #209 + #211 (issues #197/#208/#210, all TDD RED->GREEN);
  #191 closed as a dup of #192 (no code).
- [x] `scripts/version_check.py --tag v0.10.2` green; the
  `version_is_single_sourced` invariant green; no version literal pinned in
  src/ or tests/.
- [x] GitHub Release v0.10.2 -> `release.yml` (OIDC trusted publishing) green
  in 39s, incl. the built-in "verify installable from PyPI" gate; PyPI
  `0.10.2` verified (wheel 761,932 B + sdist 2,700,991 B, uploaded
  09:57:26/29); `pip index` LATEST = 0.10.2 (no CDN lag); `pip download
  --no-deps` OK.
- [x] v0.10.2 is the rollback point: `pip install brandly-cli==0.10.2`
  (previous: `0.10.1`).
- NEXT: #196 (produce auto-ref scoping — needs a product decision) + #192
  (Agnes 503: backoff / queue-status / clearer error handling).

### Round 28/256 - Bug: brandly image auto-ref opt-out + visible preset appending + dry-run (issue #212)
- [x] RED first: `tests/test_issue_212.py` (5 cases) — 4 failed on main
  (`No such option '--no-auto-refs'` / `'--auto-ref-category'` /
  `'--dry-run'`; `preset_applied` is None while `enhanced_prompt` shows the
  appended fashion language — the exact repro). 1 guard (auto-refs on by
  default, unchanged) green before and after.
- [x] Fix: `--no-auto-refs` / `--auto-ref-category` added to `brandly image`
  (matching produce/video; the category scoping additionally matches the
  category as a directory segment — v2 paths are
  `pre-production/<id>/<category>/`, so the legacy `images/<category>/`
  marker alone never matches v2). `image_analysis` records `preset_applied`
  + `preset_text` (the exact appended string) and the final prompt is
  logged. `--dry-run` prints the exact final prompt + the resolved reference
  list and exits BEFORE any write or API call.
- [x] GREEN: 29 passed (new + test_cli.py); full suite 1299 passed (was 1294);
  ruff clean; mypy clean (92 files); version-check OK (0.10.2).
- [x] PR #222 (`bug/image-style-preset-and-auto-refs`, commit `52f609c`)
  squash-merged to main; #212 auto-closed.
- NEXT: #213 (budget authoritative cost.json) + #220 (memory CLI
  exit/defaults) + #221 (401 token failure) + #219 (reference mode binding
  roles) + #192 (rate-limit warning) + #215/#217 (docs).

### Round 29/256 - Bug: cost.json is the authoritative budget cap, warn on mirror divergence (issue #213)
- [x] RED first: `tests/test_issue_213.py` (3 cases) — 2 failed on main
  (`brandly list` and `brandly status` both showed the mirror `1600` /
  `10/1600` with NO warning — the silent-revert repro). 1 guard (no warning
  when the caps agree) green before and after.
- [x] Fix (the issue's option 3, the root cause): the display reads
  `cost.json` (`budget_credits` + `credits_spent`) directly instead of the
  `project.json.budget` mirror. `cli.py` gains `_cost_authoritative()` and
  `_print_project_summary(proj, root=None)` warns on divergence;
  `cmd/production.py` `status` passes root and `list` shows the
  authoritative values with a compact `⚠` marker on diverging rows.
  `_check_budget` already read cost.json — unchanged.
- [x] GREEN: 3 passed; full suite 1297 passed (was 1294); ruff clean; mypy
  clean (92 files); version-check OK (0.10.2).
- [x] PR #223 (`bug/budget-authoritative-cost-json`, commit `56ec431`)
  squash-merged to main; #213 auto-closed.
- NEXT: #220 (memory CLI exit/defaults) + #221 (401 token failure) + #219
  (reference mode binding roles) + #192 (rate-limit warning) + #215/#217
  (docs) + #214 (preflight estimate).
