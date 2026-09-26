# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added (G7 PR 1 — brand kit, issue #98)
- **Decision records DEV-G7-001/002/003 confirmed**: project-level brand kit
  (`.brandly/<project>/brand.json` — palette, claim allowlist, style lock,
  logo + overlay spec). Never user-config or `.env` (F2).
- `brandly brand init/verify/show` — init writes + validates the kit
  (fail-closed on bad hex / unknown style / empty claims); verify exits 1 on
  missing or malformed kits; show renders the kit (text or `--json`).
- Prompt-layer brand lock (`brand_kit.apply_brand_lock`): appends palette,
  claim allowlist, and third-party-mark ban to prompts; conflicting styles
  raise `BrandLockConflict`.

### Changed
- Capability matrix: `brand_kit` is now `partial` (prompt-layer lock +
  verify shipped; gate-layer claim check + export logo overlay planned —
  G7 PR 2), then `supported` with G7 PR 2.
- README roadmap line for brand kit synced to the partial reality.

### Added (G7 PR 2 — gate claim-lock + export logo overlay, issue #98)
- **G7 closes F9 gap 2** — `brand_kit` capability is now `supported` (e2e
  dry-run proof: `brand verify` + gate claim-lock + export overlay).
- Gate layer: registered on-screen text outside the brand kit's claim
  allowlist hard-fails `brandly gate --scene/--all-scenes` (deterministic;
  blank/unregistered text never blocks; violations recorded under
  `report["brand"]`).
- Export layer: `brandly export-platforms --brand` composites the kit's
  logo via ffmpeg overlay (corner / safe-zone / opacity from the kit's
  `OverlaySpec`); missing kit, logo, or file fails closed.

### Added (G8 PR 1 — metrics ingest, issue #99)
- **Decision records DEV-G8-001/002/003 confirmed**: ingested metrics live
  project-local (`.brandly/<project>/metrics/<platform>-<date>.json`),
  never the user config store (DEV-G8-001); no network, no credentials in
  this PR (YouTube Analytics API adapter is G8 PR 2).
- `brandly metrics import <file> --platform youtube [--project <id>]` —
  versioned CSV/JSON schema `{date, views, likes, watch_time_seconds,
  ctr_pct}`; deterministic fail-closed validation (unknown platform,
  malformed row, out-of-range value).
- `brandly metrics show` — latest ingested snapshot per platform.
- `brandly analyze` now prefers the latest ingest over heuristics and
  always labels the source in its output (`ingested` vs `heuristic`,
  G5 scope-truth rule); the CTR row blends the ingested `ctr_pct`.

### Changed (G8 PR 1)
- Capability matrix: `metrics_ingest` is now `supported` (import + analyze
  blend shipped; YouTube Analytics API next step planned — G8 PR 2).
- README metrics roadmap line synced.

## [0.5.0] — 2026-09-25

### Added
- **Decision record DEV-G6-001** (`dev-notes/DECISION-G6-PUBLISH-PATH.md`):
  publish path in scope for v0.5 — YouTube first, dry-run-first,
  credential-gated; no scheduler service or UI.
- `brandly publish <id> --platform youtube [--schedule ISO] [--dry-run]
  [--json]` — dry-run renders the exact request payload and never posts;
  live posting fails closed without a stored credential.
- `brandly config set/get/list` — user-level credential store
  (`~/.brandly/credentials.json`); secrets never touch project files or
  `.env` (F2).
- `brandly capabilities` — per-persona capability matrix (text + `--json`),
  rendered from the single source list in `brandly_cli/capabilities.py`.

### Changed
- Capability matrix: `publish_schedule` is now `partial` (dry-run
  implemented; live YouTube pending credentials; TikTok/IG adapters are
  G6 follow-up PRs).
- README "What is Brandly?" rewritten to the audited reality: what runs
  today vs what is planned (roadmap lines are marked as planned, not
  claimed), linked to the audit's gap register. The CI guard
  (`tests/test_capabilities.py`) fails when a README claim has no
  capability-list entry. Open F9 gaps filed as issues #97–#99
  (publish/schedule G6 decision-gated, brand kit, metrics ingest).
- **Aspect-ratio cropping no longer happens in production** (G4, audit F8).
  Generated clips keep their source aspect; the ratio decision happens once,
  in post-production assembly. The shot loop (`shot_runner`) no longer calls
  `apply_aspect_ratio` — the function survives as the manual/post-processing
  crop tool (still covered by `tests/test_issue_48.py`).
- `brandly stitch` gained `--ratio <W:H>` and `--fit crop|pad` (default
  crop): the single assembly-time ratio owner. Crop is a center-crop at
  source scale; pad letterboxes/pillarboxes with black bars (no upscaling).
- `brandly export-platforms` gained `--fit crop|pad` (default **crop**):
  feed aspects are now center-cropped to the platform ratio instead of
  letterboxed to standard resolution; `--fit pad` restores the old
  letterbox behavior. Both paths reuse the same shared filter builders
  in `stitch.py` (`ratio_crop_filter` / `ratio_pad_filter`), and a source
  already within 2% of the target ratio is a no-op — the stitch→export
  pipeline never double-crops.

### Deprecated
- `brandly produce --aspect-ratio` is a no-op alias kept for one release:
  it prints a one-line migration notice pointing at
  `stitch --ratio <r> --fit crop` / `export-platforms --fit`.
  **Removal tracked:** delete the flag in the release after next.


## [0.4.1] — 2026-09-25

### Fixed
- CLI entry points: `python -m brandly_cli.cli` executed `main()` before the
  command groups were registered, so every command was missing
  (`Error: No such command 'list'`) — this also broke `make e2e`. Registration
  now happens lazily on first command lookup (`_LazyCommandGroup`).
- Import order: importing any `brandly_cli.cmd.<module>` before
  `brandly_cli.cli` raised `ImportError: cannot import name 'register' ...
  (most likely due to a circular import)`. Every import order now works.
- `agent_surface`'s subprocess runner decoded the CLI's stdout with the platform
  locale codec, so UTF-8 tool output (`→`, `✓`, `—`) raised
  `UnicodeDecodeError` on Windows and the tool result came back empty
  (`stdout=None`). The output is decoded as UTF-8 with replacement now.
- Test suite: the two upstream `starlette`/`anyio` `TestClient` deprecation
  warnings are silenced with message-scoped `filterwarnings` filters, so the
  suite is warning-free without hiding any new warning.

## [0.4.0] — 2026-09-25

### Added — G7: orchestrator + subagent contract layer (#90, #91, #93)
- `brandly plan <id> [--json]`: per-phase **dispatch contracts** for
  orchestrating agents — for every phase, the `inputs[]` it reads, the
  `outputs[]` it must produce, the deterministic `gate` that verifies it, the
  `next_command`, and its `est_cost`. `phase_handoffs()` (cmd layer) is the
  single data source; the command renders a table or one JSON document.
  Registered as a read-only tool in the `agent_surface` manifest (MCP +
  subprocess dispatchable), and `brandly estimate` now shares the same
  per-phase cost math (`phase_costs()`).
- Director prompt gained a **Subagent Dispatch** section: the 5-item
  per-subagent contract (scope, inputs, outputs, boundaries, verification),
  the parallel-cognition / serialized-execution rule, and the gate-screening
  loop pointing at `brandly plan <id> --json`. `brandly director` prints a
  compact dispatch table, and `brandly init`'s `AGENTS.md` points at the same
  source of truth.
- **Structured retry envelope + bounded re-dispatch**: a failed phase now
  persists an `attempts` counter in `project.phases` (`PhaseResult.attempts`)
  and returns a JSON-parseable `retry_instruction` (error/verdict, attempts vs
  `MAX_PHASE_ATTEMPTS` = 3, exact re-run command, escalation command).
  `brandly plan --json` surfaces `attempts` + `retry_instruction` on failed
  phases; `brandly run --execute` prints `Retry attempt: N/3` plus the JSON
  envelope. At the cap the phase stays `failed` and `next_command` becomes the
  `brandly approve <id> <phase>` human escalation — no unbounded re-dispatch
  (the state-only `run` path preserves the counter too).

### Fixed
- Shot runner: corrected the ratio-crop axis and made the Windows rename
  retry-safe (#92).

### Notes
- Test suite: 733 → 764 passed (G7 added 31: contracts 13, dispatch 8,
  retry envelope 7, crop/rename fix 3). ruff / mypy / import-linter clean.
- README documents the orchestrator + subagent workflow (plan → dispatch →
  screen → advance → retry/escalate).

## [0.3.26] — 2026-09-24

### Added — G1: agent-native tool surface (#81, #83, #84)
- `agent_surface.py` dispatch layer: one machine-readable tool manifest
  (`brandly tools --json`) covering the real CLI — each tool has a JSON-Schema
  parameter contract, a read-only classification, and its backing command.
  `build_command()` is a pure call→argv mapping; `dispatch()` executes library
  tools in-process and pipeline tools through an injectable subprocess runner,
  returning a fail-safe envelope (errors reported, never raised).
- `brandly mcp serve`: newline-delimited JSON-RPC 2.0 MCP server over stdio
  (`initialize`, `ping`, `tools/list`, `tools/call`) exposing exactly that
  manifest, so external agents and subagent frameworks attach brandly as a
  tool provider instead of inventing their own ffmpeg/HTTP tools.
- `brandly init` writes an `AGENTS.md` pointing agents at the tool surface
  (create-only); `brandly sync` no longer writes raw provider API keys by
  default — the old behaviour is opt-in behind `--legacy-provider-keys`.

### Added — G2: real director orchestration (#86, #87, #88, #89)
- `brandly run <id> --execute [--until <phase>] [--yes]` drives
  `Director.run_pipeline` over the 10-phase pipeline; resumable from
  `project.phases`; every phase is fail-closed (worker error → phase `failed`,
  `current_phase` frozen, pipeline stops, exit 1). No fabricated success
  paths remain.
- Real phases: `script` writes `shots.json`; `asset` invokes the
  produce/shot_runner path; `re_edit` stitches scene clips via
  `stitch.stitch_videos` → `videos/final.mp4`; `validate` runs the G3 scene
  gate (deterministic `verify_element` runner) and blocks advance on any
  non-pass verdict; `publish` calls `export_platforms` (tiktok +
  youtube_standard → `<project>/export/`).
- The fabricated `auto_direct` pipeline stub is deleted (regression test
  pins it). `brandly director` now prints the Director prompt plus the live
  orchestrator plan; `director_plan()` is the data-only plan source for
  agents (phases, per-phase status, current step, exact next command).

### Added — G3: explicit scene model + completeness gate (#85)
- `scenes.py`: `scenes.json` manifest written by `produce` BEFORE
  generation; project-unique scene ids (S01…); `status()` matrix;
  `evaluate()`/`evaluate_all()` with injected quality runner.
- `brandly scenes status [--json]` and `brandly gate --scene/--all-scenes
  [--no-quality]` (exit 0/1/2).

### Quality
- Full suite: 733 tests passing; ruff, mypy, and import-linter (L0/L1
  layering) clean. CI green on every release PR.

## [0.3.24] — 2026-09-23

### Added
- Production studio navigation now loads projects on boot, exposes real functional panels, and includes persisted loading/error states.
- Unified agent tooling for timeline inspection, clip updates/reordering, regeneration, project export, and gate verdicts.
- Frontend CI quality gate covering zero-warning Oxlint, strict TypeScript, Vite production build, and committed-bundle freshness.
- Warning-free dependency and GitHub Actions stack, including bounded Starlette compatibility and regression guards.

### Fixed
- Generated SPA bundles are deterministic across Windows and Linux line endings and platform EOF behavior.
- React effect dependencies and pointer-event handling no longer emit Oxlint/React compiler warnings.
- Quality-gate pixel inspection uses the current Pillow API without deprecation warnings.
- Release publishing uses modern action majors and verifies the published package through PyPI's version endpoint.

## [0.3.25] — 2026-09-24

### Added — #73: structured `--json` results + explicit `--output` writes
- `brandly image --output <path>` writes the artifact to exactly the requested
  destination: the provider payload is downloaded/decoded and validated
  (full-decode, format probe) before the file is moved into place, so a
  truncated or non-image response never leaves a partial file at that path.
- `brandly image --json` emits **only** one machine-readable JSON document on
  stdout (rich console output is suppressed for the whole run): success is
  `{status, task_id, provider_url, path, format, width, height, model,
  generated_at, job_id}`; failures exit non-zero with
  `{status: "error", error_code, error_message, task_id, job_id}` where
  `error_code` is one of `provider_error`, `no_image`, `image_download_failed`.
- Provider success detection is payload-driven: URL-only and base64-only
  responses both succeed; only a response carrying neither is reported as
  `no_image`.
- The prior fragile behaviour — a generated URL being reported as "Provider
  returned no image URL" — is covered by regression tests
  (`tests/test_issue_73.py`), together with output placement.

### Added — #74: durable image job records + `job-poll`
- `brandly image` now persists a job record to `ROOT/.brandly/jobs/<job-id>.json`
  **before** the provider call (`job_id`, status, prompt/model/size/seed,
  timestamps). Terminal state — artifact URL/metadata or failure reason — is
  written on success and failure, so a crash, timeout, or client disconnect
  no longer orphans the work.
- New `brandly job-poll <job-id>` command recovers finished generations from
  the durable record: `--output` writes the recovered artifact to disk,
  `--max-age` (default 48 h) expires stale records, `--json` emits a
  machine-readable body (`{status, job_id, result_available, path,
  provider_url, ...}`). Polling **never** submits a generation request.
- Credential-bearing URL query params (`api_key`, `token`, `secret`,
  `awsaccesskeyid`, `signature`, …) are stripped from persisted records
  (P1-1). The JSON machine output now includes `job_id` as the recovery
  handle; text-mode output is unchanged.

### Fixed — #75: isolate generated image metadata to the selected project context
- `brandly image` no longer falls back to an implicit `untitled` project when
  no `--project-id` is given: the URL-autosave branch created a phantom
  `pre-production/untitled/` + `.brandly/untitled/` tree under the running
  home. Without a project context the command now reports that explicitly
  (and points at `--output` / `--project-id`) and creates no project records.
- External/isolated runs are now first-class: point the context root at an
  isolated home (`ROOT` env or `brandly --root <path>`) and write artifacts
  with `--output <path>`; metadata stays beneath the selected project only.
  Documented in the README ("Running image generation externally").

### Changed — PR A: `cmd/` split (structural 10/10, P0-1)
- `cli.py` demoted to a thin registration module: command bodies live in
  `brandly_cli/cmd/{production,generation,gate,post,providers,tools}.py`,
  each with a `register(cli)` entry point; `cli.py` keeps the root group,
  shared helpers and the `register()` call (1,202 → 784 lines).
- Reference-sheet prompt templates moved from `cli.py` to
  `brandly_cli/reference_prompts.py` (re-exported by `cli.py` for
  compatibility with the cmd modules).
- All 64 command `--help` texts verified byte-identical before/after
  (snapshot in `dev-notes/_cli_snapshot_before.txt` vs `_after.txt`).

### Changed — PR B: director demotion + provider hygiene (P0-2, P1-3, P1-4)
- `brandly_cli/director.py` is now a pure prompt composer (fan-out 0):
  `DIRECTOR_PROMPT` + `get_director_prompt()`. The `Director` / `DirectorConfig`
  orchestrator classes moved to `brandly_cli/cmd/production.py` (the caller
  layer that owns provider/state calls). **Import note:**
  `from brandly_cli.director import Director` →
  `from brandly_cli.cmd.production import Director`.
- Providers (`agnes_client`, `ark_client`) no longer import the prompting
  layer: style-preset application moved to the callers (`cmd/generation.py`
  video, `cmd/production.py` batch, `cmd/providers.py` ark commands).
  The `style_preset` keyword was removed from `agnes_client.generate_image` /
  `create_video_task` and `ark_client.generate_image`; the Ark video task's
  previously hard-coded "cinematic" preset is now applied explicitly by the
  callers (behavior preserved). Unit tests updated from provider-side to
  caller-side assertions.
- `agent_tools ⇄ agnes_client` import cycle broken via new
  `brandly_cli/job_polling.py` (shared tool-result serialization, `to_json`
  — re-exported from `agent_tools`). Static graph: zero hard cycles, zero
  upward provider→prompting edges (`python scripts/import_graph.py`).

### Changed — PR C: utils split + import-linter + layout contract tests (P1-5, P2-6, P2-8)
- `brandly_cli/utils.py` (kitchen-sink, fan-in 8) split into
  `brandly_cli/io.py` (JSON I/O, downloads, timestamps, sanitizers, skill
  discovery) and `brandly_cli/planning.py` (generation/production plans).
  `utils.py` kept as a deprecated re-export shim so existing imports keep
  working; will be removed in a later release.
- `_record_media_spend` / `_human_review_gate` / `_save_artifact` moved out
  of `cli.py` into their testable modules (`cost_tracker`, `gates`, `io`)
  with backward-compatible deprecated aliases in `cli.py`.
- `.importlinter` config added with L0–L5 layered contracts matching
  `ARCHITECTURE-DIAGRAM.md` §5; `no-import-cycles` contract with
  `ignore_impossibles` for the intentional `cli ⇄ cmd.generation` deferred
  register cycle. Added to dev deps and CI (`ruff -> import-linter -> mypy`
  pipeline). A deliberate upward import in a scratch file fails the lint.
- Two v2-layout idempotency tests added:
  `test_init_v2_then_migrate_is_idempotent` and
  `test_v1_to_v2_then_migrate_again_is_idempotent`.
- `cli.py` final size: 361 lines (down from 1,202). Structural groundedness
  raised from 8/10 -> 10/10.

## [0.3.18] — 2026-09-23

### Added — production-pipeline issues #31–#43 (PR #44)
- **Structured prompts (#31):** shot `prompt` may be an 8-layer dict
  (`subject/emotion/optics/motion/lighting/style/audio/continuity`),
  expanded by `video_prompts.expand_structured_prompt`; unknown keys fail
  loudly at flatten time.
- **Scene-aware boilerplate (#32/#38):** `build_enhanced_video_prompt`
  honours shot-specified `[LIGHTING]/[COLOR GRADE]/[VISUAL STYLE]` over
  generic presets; `no_boilerplate: true` opts out; IDENTITY LOCK now only
  for characters present in the shot (`characters`/`character` keys).
- **Storyboard keyframes (#33):** new `brandly storyboard <project>
  --shots …` — cheap keyframe generation + offline composition gate before
  video credits; resumable via `storyboard_progress.txt`.
- **Gate policy documented/configurable (#34):** `brandly gate
  --threshold N` score floor and `--lenient` mode; active policy + score
  comparison written into gate reports.
- **Duration validation (#35):** plan-time warnings for shots over the
  Agnes effective clamp; `brandly produce --split-long-shots` slices them
  into uniform parts.
- **Live project.json (#36):** `sync_production_state()` keeps status,
  current_phase, shot_count and budget (reconciled with cost.json) fresh
  during produce runs, with phase-transition timestamps.
- **Shot-ID plans (#37):** plan files named `plan_video_<shot_id>_<ts>.md`,
  production-plan table gains a Shot ID column (legacy 7-column tables
  still parse); runner-path shots registered on the plan by default
  (`--no-plan` for legacy behavior).
- **Retry/backoff logging (#39):** `brandly produce --retries N`; progress
  lines now carry `RETRY retry=N backoff=Xs <reason>` and terminal
  `FAIL retry=N` entries.
- **Aspect-ratio post-processing (#40):** `brandly produce
  --aspect-ratio 2.39:1` center-crops generated clips to the target ratio
  via ffmpeg.
- **Reference format standardization (#41):** `brandly reference
  --format jpg|png` (default jpg) converts plates, removes duplicate-format
  twins, warns on sub-512px sources.
- **Prompt section model (#42):** `[CONSTRAINTS]` = technical limits only;
  `[NEGATIVE]` = visual exclusions only — no overlapping entries.
- **v2 project layout (#43):** `brandly migrate <project> [--apply]`
  restructures into `.brandly/` (docs/config) + `pre-production/` (assets)
  + `production/` (outputs); `brandly init --layout v2`; media roots
  resolve v2-aware via `layout.resolve_media_root`.

### Added — bundled skills wheel packaging (PR #45)
- `skills/` force-included into the wheel under `brandly_cli/skills/` so
  pip installs discover bundled skills via
  `utils.find_skills_directory` (new `__package_dir__` discovery step).
- `brandly-screenplay-architect` skill bundled.
- `tests/test_skills_packaging.py` packaging + discovery regression tests.

### Fixed
- `init` `layout_version` stamp made mypy-clean (`model_copy(update=…)`).

## [0.3.16] — 2026-09-21

### Added
- `brandly produce` progress-file runner (`src/brandly_cli/shot_runner.py`):
  a structured shot-list schema (`{"character": ..., "acts": {...}}` with
  per-act prompt `prefix`, `style`, `folder` and plate-stem `refs`/`ref`s),
  plus new flags `--no-auto-refs`, `--character`, `--allow-referenceless`,
  `--max-wait`, `--only` and `--max`. Any of these (or the structured
  schema) routes the run through a resumable progress file
  (`.brandly/<project>/docs/tmp/produce_progress.txt`) instead of the
  production-plan loop, so film production no longer needs an external
  runner script:
  - generated clips are renamed to a deterministic, assembly-friendly
    convention — `Scene-<scene:02d>-Shot-<scene>-<shot-in-scene>.mp4`
    (e.g. `Scene-01-Shot-1-2.mp4` for the second shot of scene 1). The
    scene number comes from an act-level or shot-level `"scene"` key, else
    the act's position in the shot list; the trailing number is the shot's
    position inside that scene. A redo replaces the previous take;
  - plate-stem references resolve under `images/<category>/`, preferring
    the optimized `<stem>.opt.jpg` twins (small reference payloads —
    issue #20 free-tier timeouts);
  - a top-level / `--character` identity anchor attaches only to shots
    whose references include a character plate;
  - transition shots (`"folder": "transition"`) have their clips moved
    to `videos/transition/`;
  - a post-generation step failure (e.g. quality-gate crash) still counts
    as OK when a non-empty clip was downloaded (zero-byte / stranded files
    do not count), and the run stops on the first unrecovered failure
    (re-run the same command to resume). `--only` redoes the named shots
    even if a previous run already recorded them as OK;
  Flat shot lists without the new flags keep the existing production-plan
  behaviour. The routing to the resumable runner is announced on stderr,
  and both produce paths now pass scene/shot numbers through to the
  download (flat lists: scene 1, shot order = list order).
- `brandly video --scene <n> --shot <n>`: name the downloaded clip with the
  deterministic `Scene-<scene:02d>-Shot-<scene>-<shot>.mp4` convention
  (both flags required together; without them the timestamped name stays).
- `layout.media_root(proj_dir, "images"|"videos"|"audio")`: the
  un-categorised media top folder (used by the produce runner).

### Fixed
- `brandly produce`: the legacy production-plan loop lost its flat-schema
  narrowing when the runner landed, failing `mypy` with 5
  `attr-defined`/`arg-type` errors — restored.
- `brandly stitch`: multi-clip graphs chained xfade/acrossfade through
  dangling filter labels — virtual labels are now chained correctly.
- Quality gate: a locked temp frame (WinError 32 from antivirus / the search
  indexer on Windows) no longer hard-fails `brandly gate` / `brandly video`
  after the generated artifact is already on disk.
- `tests/test_reference.py`: the stale-reference test was an unmocked
  network call that could spend credits with a key set — now fully mocked.

## [0.3.15] — 2026-09-20

### Added
- Image converter (`src/brandly_cli/image_convert.py`): large local reference
  images auto-shrink to webp/jpeg before base64 upload (JPEG for opaque
  images, WebP when alpha must be preserved; only when it saves ≥ 10 KB;
  opt-out with `BRANDLY_IMAGE_CONVERT=off`).
- `brandly produce <project_id> --shots shots.json`: multi-shot film
  production driven by the production plan (`docs/plan/production_plan.md`,
  the source of truth). ALL shots are registered on the plan first, then
  generated **one shot at a time** with a 60 s wait between requests (Agnes:
  1 request/minute). No batch/parallel mode. Resumable: COMPLETED shots are
  skipped, a failure stops the run and remaining shots stay PENDING.
- `brandly video --no-auto-refs` and `--auto-ref-category <name>` to scope
  auto-injected reference images (issue #20).
- `brandly reference <project_id> --image <path> [--no-generate]` to import
  an existing plate as `primary_reference` without generating (issue #23).
- `brandly batch --interval` (default 60.0 s): rate-limited variant
  submission, kept as the future batch path for when Agnes supports true
  batch (decision: batch NOT removed).

### Fixed
- `create_video_task` takes `style_preset` — the preset now follows `--style`
  (cinematic only for cinematic) instead of being hardcoded; disabled for
  non-photographic styles (issue #21).
- Video create failures print `ExceptionType: detail` — empty timeout
  messages no longer vanish; create timeout raised 60 s → 180 s (issue #24).
- `brandly jobs` degrades gracefully on HTTP 404 (unsupported endpoint)
  with a hint to use `brandly job-resume <video_id>` (issue #19).
- Skills/docs aligned: `refs/` → `images/<category>/` (single layout),
  storyboard + video-generation skills document `brandly produce`,
  troubleshooting model pin corrected to `agnes-video-2.5-flash`.
- README documents `brandly produce`, the converter, scoped refs and the
  reference import; `.env.example` documents `BRANDLY_IMAGE_CONVERT`.

### Closed issues
- #19, #20, #21, #22, #23, #24.

## [0.3.14] — 2026-09-20

- Single layout (no refs/), plan reuse + production plan, HITL gates,
  keyframe archiving.
