# brandly-cli — Architecture Report

> Generated after resolving production-pipeline issues #31–#43 (GOAL-ISSUES-31-43.md).
> Repo: `Dream-Pixels-Forge/brandly-cli` · ~18.8k lines of Python across 39 modules · 64 CLI commands · 500 tests.

## 1. What this project is

`brandly-cli` is a pip-installable Python CLI (`brandly`) that orchestrates the full
AI film-production pipeline on the Agnes model family (plus Minimax/Ark providers):
script → references → storyboards → video takes → quality gates → audio → assembly →
export. It is a **state machine on disk**: every decision is persisted under a project's
`.brandly/<project>/` tree, which makes long, rate-limited productions resumable.

Design invariant: **determinism and resumability over convenience**. A 61-shot
production run must survive machine reboots, API outages and human review pauses;
every loop is either idempotent or records progress in a plain-text log.

## 2. Module map (by responsibility)

### 2.1 Foundation layer

| Module | Responsibility |
|---|---|
| `layout.py` | **Single source of truth for on-disk paths.** Folder taxonomy (`docs/`, `images/<category>`, `videos/<category>`, `audio/<category>`, `3d-spatial/`), eager dir creation, media discovery. New in #43: **v2 layout** — `pre-production/<p>/` + `production/<p>/` roots, `is_v2_layout()` / `resolve_media_root()` detection via `project.json layout_version=2`. |
| `types.py` | Pydantic models: `ProjectData` (project.json, `extra="allow"`), `PhaseResult`, script/concept models. |
| `project_manager.py` | Async CRUD for `project.json`; `update()` auto-creates projects. New in #36: `sync_production_state()` — the single live-state writer (status/phase/shot_count/budget reconciliation/phase timestamps). |
| `cost_tracker.py` | `cost.json` ledger; `record_spend` enforces budget caps. |
| `constants.py` | Model registries (Agnes video/image/text, Minimax, Ark) with `cost_credits` + `max_duration` metadata; style/lighting/grade vocabularies. |
| `utils.py` | Cross-cutting helpers: JSON I/O, `write_generation_plan()` (pre-API intent records, signature-based reuse), production-plan table (8-column with Shot ID, backward-compatible 7-column parsing), `write_generation_doc()`, file download, project-id validation. |

### 2.2 Prompt engineering layer

| Module | Responsibility |
|---|---|
| `video_prompts.py` | The 8-layer film-direction prompt core. Section model (#42): `[CONSTRAINTS]` = technical limits only, `[NEGATIVE]` = visual exclusions only — no overlap. `expand_structured_prompt()` (#31) turns shot dicts into directed prompts (unknown keys fail loudly); `detect_scene_direction()` (#32) makes boilerplate scene-aware; builders for single/multi-shot/keyframe/showcase prompts; `ShotChain` for continuity-linked sequences. |
| `style_presets.py` / `director.py` | Style vocabularies; director-level orchestration (per-shot prompt enrichment). |
| `cinematic_enhancer.py`, `analyzer.py` | Enhancement heuristics + structural analysis of prompts/scenes. |

### 2.3 Pipeline layer

| Module | Responsibility |
|---|---|
| `shot_runner.py` | **Pure-logic resumable runner** (no CLI deps): `flatten_shots()` (structured acts → flat `Shot` list with reference-plate resolution + character presence + dict-prompt expansion), `ProgressLog` (plain-text OK/RETRY/FAIL lines — #39 semantics), `RunnerConfig`/`run_shots()` (rate limiting, retries, aspect-ratio post-crop #40, `on_shot_done` hook), `split_long_shots()` (#35), deterministic `Scene-XX-Shot-X-Y` clip naming. |
| `quality_gate.py` | Anti-slop/drift gate: deterministic pre-checks (presence/decodability/blank guard) + Agnes multimodal verdict. Policy module (#34): artifact cutoffs (`distortion≥6, slop≥7, drift≥6`), optional `threshold` score floor, `lenient` mode; the active policy is written into every report. |
| `stitch.py`, `edit.py`, `beat_sync.py`, `dubbing.py`, `captions.py`, `sync.py` | Post-production: assembly, trimming, beat sync, dubbing, captions, timing. |
| `export_platforms.py`, `sharing.py`, `webhook.py` | Export presets per platform + share/webhook delivery. |
| `spatial_tracker.py`, `blender_integration.py` | 3D spatial reference frames (Blender) + camera/keyframe/depthmap tracking. |
| `memory.py`, `autodirector.py`, `issue_tracker.py`, `trends.py`, `agent_tools.py`, `templates.py`, `thumbnails.py`, `layout.py` | Supporting services. |

### 2.4 Provider clients

| Module | Notes |
|---|---|
| `agnes_client.py` | Primary provider: `generate_image`, `create_video_task`/`poll_video`, `chat_completion` (multimodal gates), retries with backoff, 1 req/min rate-limit handling. |
| `minimax_client.py`, `ark_client.py`, `audio_client.py` | Secondary providers (music/TTS/image/video alternatives). |

### 2.5 Orchestration

`cli.py` (~5,000 lines) is the **only module that knows about Click**. It wires
foundation + prompt + pipeline modules into 64 commands. Two production paths matter:

* **Flat path** (`produce` without runner flags): every shot is registered on the
  production plan *before* generation (`write_generation_plan`), then pulled one at
  a time — the plan table is the source of truth.
* **Runner path** (structured shot lists / `--no-auto-refs` / `--only` / `--max`):
  progress-file runner (`docs/tmp/produce_progress.txt`) + per-shot plan rows (#37),
  project.json live sync (#36), retries (#39), aspect post-processing (#40),
  duration validation + splitting (#35).

Both funnel into `_generate_shot()` → `brandly video` command → pre-plan → Agnes
task → post-generation gate → human gate → credit recording (`_record_media_spend`).

## 3. Data model (on disk)

```
<root>/.brandly/<project>/            ← config + docs (v1 layout)
    project.json      status, current_phase, shot_count, budget, spent,
                      phases{phase:{status,started_at,completed_at}},
                      layout_version (2 ⇒ v2), primary_reference
    cost.json         budget_credits + spend ledger (CostTracker)
    docs/plan/        production_plan.md (8-col table incl. Shot ID)
                      plan_video_<shot_id>_<ts>.md (per-shot intent records)
    docs/bible/       production bibles (2.39:1, style, character rosters)
    docs/storyboard/  storyboards / shot lists
    docs/tmp/         produce_progress.txt, storyboard_progress.txt,
                      gate_<kind>_<ts>.md reports, fail docs
    images/<category>/ reference plates (.opt.jpg twins preferred),
                       keyframe/, storyboard/
    videos/scenes/    Scene-XX-Shot-X-Y.mp4 takes (re-runs supersede)
    videos/transition/, insert/, general/
    audio/…           soundtrack/sfx/foley/voiceover
<root>/pre-production/<project>/      ← v2 (post-migrate): character/ location/
<root>/production/<project>/…        prop/ storyboard/ + videos/ + audio/
```

**Resumability model:** a shot is *done* iff its `OK` line exists in the progress
log (`completed_ids` only trusts the shot-id + status fields — free-text notes can
never fake completion). `RETRY`/`FAIL` lines are history + diagnostics (#39).

## 4. Issue → code traceability (#31–#43)

| # | Fix | Where |
|---|---|---|
| 31 | 8-layer structured prompt schema | `video_prompts.expand_structured_prompt`, `shot_runner.flatten_shots`, flat produce path |
| 32 | Scene-aware boilerplate | `detect_scene_direction` + `build_enhanced_video_prompt(shot_lighting/grade/style, no_boilerplate)` wired in `brandly video` |
| 33 | Storyboard keyframe gate | `brandly storyboard` command + `images/storyboard/` category + `storyboard_progress.txt` |
| 34 | Gate threshold documented/configurable | `quality_gate` policy constants, `--threshold`, `--lenient`, report policy line |
| 35 | Duration validation + split | plan-time warnings in `_run_produce_runner`, `shot_runner.split_long_shots`, `--split-long-shots` |
| 36 | project.json live sync | `project_manager.sync_production_state` (status/phase/shot_count/budget/phases) called at runner start/end |
| 37 | Shot-ID plan naming | `write_generation_plan(shot_id, scene, act)`, 8-column production plan table, per-shot plan rows on runner path |
| 38 | Present-characters identity lock | `characters`/`character` presence declarations in `flatten_shots` + `_presence_character` (flat path) |
| 39 | Retry/backoff logging | `ProgressLog.record(retry, backoff)`, `RunnerConfig.retries/retry_backoff`, `--retries` |
| 40 | Aspect-ratio enforcement | `--aspect-ratio` post-crop (`shot_runner.apply_aspect_ratio`), ffmpeg center-crop, ~2% tolerance no-op |
| 41 | Reference format standardization | `--format jpg\|png` on `brandly reference`, twin dedupe, <512px warning |
| 42 | CONSTRAINTS/NEGATIVE separation | module docstring section model + `technical_constraints()`/`negative_block()` in all builders |
| 43 | Folder restructure + migrate | `migrate.py` (dry-run/--apply), `init --layout v2`, `layout.resolve_media_root` v2 awareness |

## 5. Test & CI architecture

* **Unit layer:** pure-logic modules tested without the CLI (`shot_runner`,
  `video_prompts`, `quality_gate`, `layout`, `utils` production-plan parsing).
* **CLI layer:** `CliRunner` end-to-end against tmp project trees
  (`test_issues_19_24.py` legacy reference semantics, `test_issues_31_43.py` new
  behaviors, `test_cli.py` core commands).
* **Packaging layer:** `test_skills_packaging.py` — wheel force-includes
  `skills/` under `brandly_cli/skills` and `find_skills_directory` discovers it
  (CI installs the package editable, so installed-package shadowing seen locally
  is an environment artifact, not a test failure).
* **CI (GitHub Actions):** Python 3.10/3.11/3.12 matrix — ruff, mypy, py_compile,
  pytest+coverage, wheel build + twine check.

## 6. Structural observations / risks

1. **`cli.py` monolith (5.3k lines).** All 64 commands live in one module. The
   clean seams (foundation / prompt / pipeline / provider) exist in the other
   modules; a future `cmd/` split (one file per command group) is the natural
   next refactor — the runner/governance additions from #31–#43 made this more,
   not less, valuable.
2. **Two produce paths with subtly different guarantees.** The flat path writes
   plan rows for every shot; the runner path now does too (#37), but only when
   `--no-plan` is not set. A reviewer should treat `docs/plan/production_plan.md`
   as the audit trail and `docs/tmp/produce_progress.txt` as the resumability
   ledger.
3. **v2 layout is opt-in and additive.** Nothing breaks for v1 projects; the
   detection rule is `layout_version=2` in project.json, else presence of
   `pre-production/<project>/`. The only consumer difference is the media root
   for runner/storyboard/reference-resolution paths.
4. **Gate policy is now explicit but the score floor is off by default**
   (pre-checks + artifact cutoffs only). `--threshold 90` reproduces the
   stricter production behavior reported in #34.
5. **Agnes model limits are constants, not API facts.** `AGNES_MAX_SHOT_DURATION`
   (12s nominal) and the 6s effective clamp (`SPLIT_SEGMENT_DURATION`) encode
   observed behavior; when the model ceiling changes, both and the production
   bibles need updating together.
6. **Windows-specific artifacts** (`nul` stray file in repo root; LF→CRLF
   warnings) should be gitignored/cleaned in a chore pass.

## 7. How to read a production from disk

```
plan_video_s10_04_<ts>.md   → intent (prompt, model, shot id, act/scene)
production_plan.md row      → status of every plan (PENDING/COMPLETED/FAILED)
produce_progress.txt        → OK/RETRY/FAIL history with retry counts + backoff
gate_<kind>_<ts>.md         → what the gate saw + the policy that applied
project.json                → live status/phase/shot_count/budget (kept fresh by #36)
cost.json                   → authoritative spend ledger
Scene-XX-Shot-X-Y.mp4       → deterministic clip names; -2/-3 suffixes = extra takes
```
