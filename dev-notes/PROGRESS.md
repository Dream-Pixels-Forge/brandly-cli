# Pipeline Progress — brandly-cli

## Current State
- Project: brandly-cli
- Started: 2026-09-07
- Version: 0.7.0 (shipped via #147; backlog CLEAR — #148–#152 closed by PR #153; #154 open: Windows console glyph encoding)
- Current Phase: Phase 3 (Engineer) — Feature Implementation
- Status: in-progress (backlog closed; publish path shipped across all three F9 platforms)
- Test Count: 1076 passed (0 xfail/xpass)
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


