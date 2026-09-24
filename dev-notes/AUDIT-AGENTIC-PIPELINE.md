# AUDIT — Agentic system, director orchestration, scenes, gates, aspect ratio

> **Project:** brandly-cli · **Date:** 2026-09-24 · **Base:** `main` @ 9fedee4 (v0.3.25)
> **Trigger:** external report — "AI tools (opencode/Claude-style) invent their own
> tools instead of using brandly-cli's; the director agent does not orchestrate
> idea → finished product; the scenes system is broken and has no per-scene gate;
> aspect-ratio cropping must live in post-production/assembly only."
> **Method:** static read of `src/brandly_cli/**`, `tests/**`, README, plus
> `python -m brandly_cli --help` (60-command surface) and repo-wide regex sweeps
> for `mcp`, `run_pipeline`, `aspect`, `scene`, `agent_tool`.

## Verdict summary

| # | Finding | Severity | Reported symptom confirmed |
|---|---------|----------|----------------------------|
| F1 | Brandly's tool surface is never exposed to external agents (no MCP, no manifest) | **Critical** | yes |
| F2 | `brandly sync` injects raw provider keys into agent configs — bypass is designed in | **Critical** | yes |
| F3 | `brandly run` executes nothing; the real orchestrator (`run_pipeline`) is dead code | **Critical** | yes |
| F4 | Phase workers are partly hard-coded stubs (`concept`, `asset`, `re_edit`, `publish`, `auto_direct`) | **High** | yes |
| F5 | README claims an autonomous pipeline + director orchestrator that do not exist | **High** | yes |
| F6 | Scene identity is positional/implicit — no explicit scene model | **High** | yes |
| F7 | No scene/shot completeness gate anywhere (flat counts only) | **High** | yes |
| F8 | Aspect-ratio cropping happens **in production**, not assembly | **High** | yes |
| F9 | Scope gaps for creators/marketers (no publish/schedule; studio can't run the pipeline) | **Medium** | yes |

Nothing below is inferred: every claim carries a `file:line` anchor.

---

## F1 — Agent tool surface never reaches external agents · CRITICAL

**Evidence**
- `src/brandly_cli/agent_tools.py:1-13` — the tool handlers are wired *only* to the
  Agnes model: "The tool *descriptor* (name + JSON schema) is exposed to the Agnes
  model via the OpenAI-compatible `tools` field". The docstring is explicit that the
  set is "intentionally small and read-only".
- `src/brandly_cli/agent_tools.py:426-437` — `get_builtin_tools()` feeds
  `agnes_client`'s agent loop: not a CLI command, not a server.
- Repo-wide sweep for `mcp|MCP|modelcontextprotocol` → **zero real hits** (the only
  match, `src/brandly_cli/cmd/gate.py:45`, is the substring inside another word).
- `python -m brandly_cli --help` lists 60 commands; **none** exports tool schemas or
  serves tools (no `mcp`, no `tools list`, no `tools call`).
- README:102-125 ships *prose skills* (`npx skills add <github-url>`), which an agent
  reads and then re-implements as ad-hoc ffmpeg/Python.

**Impact** — an external agent (opencode, Claude Code, Codex, pi) has **no
machine-consumable way to call `brandly produce`, `brandly gate`, or `brandly
stitch`**. Its only rational behaviour is to invent tools: raw HTTP to the providers
plus hand-rolled ffmpeg. This is the reported symptom, and it is architectural —
not model error.

## F2 — `brandly sync` hands agents the raw provider keys · CRITICAL

**Evidence**
- `src/brandly_cli/sync.py:18-25` — `TOOLS` maps config paths for
  `~/.qwen/settings.json`, `~/.claude/settings.json`, `~/.gemini/settings.json`,
  `~/.codex/config.toml`, `~/.pi/agent/auth.json`, `~/.opencode.json`.
- `src/brandly_cli/sync.py:200-225` — `_sync_opencode()` writes `apiKey` **and**
  `baseUrl` for Agnes/MiniMax straight into `~/.opencode.json`.
- `src/brandly_cli/cmd/tools.py:37-44` — `brandly sync`'s own docstring: "write
  Brandly API keys into them so they can use Agnes AI (image/video) and MiniMax
  (audio) **directly**."
- `src/brandly_cli/sync.py:228-241` — `_sync_dotenvs()` additionally appends both
  keys to **every** `.env` found under cwd, `~`, `.brandly/**`, `projects/**`.
  `dev-notes/SECURITY.md:40-41` already lists ".env files found in project
  directories" as a security finding.

**Impact** — the CLI's published integration story teaches agents to talk to the
providers directly, so the pipeline (naming, scene registry, gates, retries, cost
tracking, production plan) is bypassed by construction. It also sprawls long-lived
provider secrets into agent config files and arbitrary `.env` files.

## F3 — `brandly run` does no work; the real orchestrator is unreachable · CRITICAL

**Evidence**
- `src/brandly_cli/cmd/production.py:208-242` — `run()`: reads the project, sets
  `phases[current] = PhaseResult(status="running")`, prints
  `"Next: approve with brandly approve <id> <phase>"`. **No work is dispatched.**
- `src/brandly_cli/cmd/production.py:244-310` — `approve()` checks
  `_check_phase_artifacts` (presence only, `cli.py:225-268`) and flips the phase to
  `completed`.
- `src/brandly_cli/cmd/production.py:1457-1494` `Director.run_phase()` /
  `1496-1603` `_run_phase_real()` / `1605-1624` `run_pipeline()` are the only code
  that dispatches real work — and `run_pipeline()` has **zero callers** (repo-wide
  grep: the single other hit, line 1614, is its own internal call).
- No web route invokes it: `src/brandly_cli/web/routes/` contains `projects,
  timeline, clips, gate, export, waveform, config` only — the studio cannot run the
  pipeline either.
- `tests/` contains **no** test for `run_phase`, `_run_phase_real`, or `run_pipeline`.

**Impact** — the "autonomous pipeline" is a status state machine with a manual
approval button. `run` + `approve` move `current_phase` while `PHASE_ORDER`
(`constants.py:66-90`) advertises `init → trends → concept → script → asset →
audio → re_edit → validate → publish → done` — an orchestration promise the CLI
does not keep.

## F4 — Phase workers are stubs · HIGH

**Evidence** (`src/brandly_cli/cmd/production.py:1496-1603`, `_run_phase_real`)
- `concept` (1516-1523) returns **hard-coded** concepts: `{"id": 1, "name": "Hero
  reveal"}`, `{"id": 2, "name": "Lifestyle integration"}`.
- `asset` (1540-1561) loops `shot_count` times generating the *same* prompt
  `f"{name} — shot {i+1}: dynamic product showcase"` with `wait=False` and
  `aspect_ratio="16:9"` (1552). It bypasses `brandly produce`/`shot_runner`
  entirely: no scene ids, no `Scene-XX-Shot-X-Y` naming, no identity anchors, no
  retries, no per-shot gates, no production-plan rows.
- `re_edit` (1570-1571) returns `"Review and refinement complete (stitch/captions
  not yet wired)"` — the assembly phase does not assemble.
- `publish` (1594-1598) returns `"Export ready — run brandly export <id>"`.
- `src/brandly_cli/autodirector.py:47-95` — `auto_direct()` returns
  `{"status": "script_parsed", "output_path": None}` with the real steps left as a
  comment ("In a full implementation, this would: 1. Call video generation API … 5.
  Export final video"). Its only caller is `tests/test_autodirector.py:53-67` — no
  CLI command exposes it: **a test-locked non-feature**.
- `src/brandly_cli/cmd/generation.py:1777-1782` — `brandly director` prints a prompt
  panel (`get_director_prompt()`) and nothing else.

**Impact** — "the director agent does not orchestrate accurately" is confirmed
literally: three separate things are called "director" (prompt text, a stub async
function, an unreachable `Director` class) and none drives idea → finished video.

## F5 — README overclaims vs code · HIGH

**Evidence**
- README:27 — `"Multi-agent pipeline — automated workflow from idea → trends →
  concept → script → assets → audio → validate → publish"`.
- README:28 — `"Director orchestrator — an autonomous agent that guides the entire
  production process"`.
- README:160-167 — Quick Start instructs `brandly run` → `brandly approve` →
  `brandly director`; README:288 documents `brandly run` as "Run the next pipeline
  phase".

**Impact** — a user (or an LLM treating the README as ground truth) is told the
autonomous path exists, runs it, watches phase flips with no artifacts, and then
hand-rolls their own tooling — feeding F1 again.

## F6 — Scene identity is positional, not modelled · HIGH

**Evidence**
- `src/brandly_cli/shot_runner.py:270-271` — `act_scene = as_int(act.get("scene"),
  act_position)`: a scene number is silently derived from the act's list position.
- `src/brandly_cli/shot_runner.py:333-334` — `scene=as_int(shot.get("scene"),
  act_scene)`, `index_in_scene=shot_position`: shot numbers are list positions.
- `src/brandly_cli/shot_runner.py:104-114` — `clip_filename()` produces
  `Scene-{scene:02d}-Shot-{scene}-{index_in_scene}.mp4`: the scene number is
  duplicated in the stem, and `index_in_scene` has no stability guarantee if a shot
  is inserted or reordered.
- `src/brandly_cli/shot_runner.py:162-174` (#50) appends the act slug to filenames
  to stop collisions — the *name* was patched; two acts still each own their own
  `scene 1..N` namespace, so "scene 7" is ambiguous project-wide.
- `src/brandly_cli/types.py` — no `Scene` model exists (only `ScriptResult`).

**Impact** — there is no authoritative answer to "which shots make up scene N, and
are they all done?". Every downstream feature (gates, assembly order, redo,
progress) guesses from filenames.

## F7 — No scene/shot completeness gate · HIGH

**Evidence**
- `src/brandly_cli/quality_gate.py` — zero scene concept; the only `scene` hits are
  an AI prompt hint (86) and a "repetitive scene descriptions" text heuristic
  (959-964). `verify_element()` gates a *single artifact*.
- `src/brandly_cli/cmd/tools.py:207-238` — `_print_missing_assets_summary()` computes
  `missing_videos = max(0, shot_count - len(video_files))`: a flat count. It cannot
  detect "scene 7 shot 3 is missing" or "scene 7 shot 3 rendered but failed its
  gate".
- `cli.py:225-268` — `_check_phase_artifacts()` does existence checks per phase, with
  no per-scene matrix.
- `src/brandly_cli/web/routes/gate.py:14-15` — the studio gate endpoint runs the
  deterministic gate for one `clip_id`; no scene aggregate exists to expose.

**Impact** — the reported "no gate that evaluates whether all shots of scene N were
created" is confirmed. A scene can ship with shots silently missing, stale (a redo
left the old take), or quality-FAILED, and every status surface still reads green.

## F8 — Aspect-ratio cropping runs inside production · HIGH

**Evidence**
- `src/brandly_cli/shot_runner.py:424-426` — config field docstring: "Target aspect
  ratio … When set, every freshly generated clip is cropped to it after naming
  (issue #40)."
- `src/brandly_cli/shot_runner.py:550-640` — `apply_aspect_ratio()` (ffmpeg crop),
  called at **752-772 inside the shot loop**, immediately after a clip is named: the
  destructive crop happens mid-production, per clip, before any review and again on
  every redo.
- `src/brandly_cli/cmd/production.py:442-446` — `brandly produce --aspect-ratio`
  help: "Crop every generated clip to this aspect ratio"; wired at 549.
- `src/brandly_cli/cmd/production.py:1552` — the `asset` phase hard-codes
  `aspect_ratio="16:9"` at generation time.
- Post-production owns a *different*, non-destructive policy: `cmd/post.py:181-205`
  (`resize --aspect` → scale) and `export_platforms.py:163-186`
  (`scale=…:force_original_aspect_ratio=decrease` = letterbox/pillarbox, never
  crops).

**Impact** — two modules disagree about one concern, and the irreversible decision
(crop) is taken at the most expensive point and baked into the master clip; assembly
and platform export then compound it (double-crop / letterboxed crop). Requirement:
cropping belongs to assembly/export only — production must deliver source-aspect
masters.

## F9 — Scope gaps for filmmakers / creators / marketers · MEDIUM

Verified against `python -m brandly_cli --help` (60 commands) and `web/routes/`.

| Persona need | Status | Evidence |
|---|---|---|
| Shot-by-shot generation with retries/resume | ✅ supported | `produce` + `shot_runner` (retries 775-785, resume via `completed_ids`, #49/#50 naming) |
| Storyboard, references, sheets, blocking | ✅ supported | `storyboard`, `reference`, 13 bundled skills |
| Assembly, captions, dub, beat-sync, thumbnails, platform export | ✅ supported | `stitch`, `captions`, `voice-match`, `beat-sync`, `thumbnail`, `export-platforms` |
| Scene-level completeness / QC gate | ❌ missing | F6, F7 |
| One-command idea → finished video | ❌ missing | F3, F4 |
| Agent-native pipeline control | ❌ missing | F1, F2 |
| Publish / schedule to TikTok-IG-YT | ❌ missing | `export`/`export-platforms` only write files; `share` returns a link |
| Brand-kit enforcement (logo/colour/claim lock) | ❌ missing | no `brand` command; style presets only |
| Campaign multi-variant A/B at scale | ⚠️ partial | `batch` exists; no variant matrix or scoring loop |
| Performance feedback loop | ⚠️ partial | `analyze` is a heuristic predictor; no real metrics ingest |
| Studio UI drives the pipeline | ❌ missing | `web/routes/` = projects/timeline/clips/gate/export/waveform/config |

**Verdict:** the *generation* half of the "go-to tool" promise is real and strong.
The *pipeline* half (orchestration, scene QC, publish, brand enforcement) is claimed
but absent — so today brandly-cli is an excellent **media toolkit** that leaks its
users (and their agents) back to hand-rolled tooling after generation.

---

## Confirmed-working (must not regress while fixing)

- `produce`/`shot_runner`: retry+backoff logging, resume, canonical naming (#49/#50),
  character-presence anchoring (#38), structured 8-layer prompts (#31).
- Per-artifact quality gate (`quality_gate.py`): deterministic pre-checks + AI
  verdict, policy thresholds, report artifacts.
- Durable image jobs + `job-poll` recovery (#74); project-context isolation (#75).
- Image `--json` / `--output` contract (#73); 60-command CLI surface.
- CI gates: import-linter layers, mypy, ruff, oxlint/TS/Vite bundle freshness.

## Housekeeping completed with this audit

Two phantom project trees created by the pre-#75 bug were removed from the working
tree (both git-ignored via `.gitignore:2 .brandly/`; 21 stale files total):
`.brandly/untitled/docs/tmp/image_2026*_{md,json}` and
`.brandly/undefined/{project.json,docs/plan/*,images/**,videos/**,audio/**,3d-spatial/**}`.
`.brandly/` now contains only the real project `passport-rush-taxi-chase`.

## Reproduction (all read-only)

```bash
python -m brandly_cli --help            # 60 commands, no tools/mcp surface
python -m brandly_cli run <project-id>  # flips state, does no work
python -m brandly_cli director          # prints a prompt panel
```

Sweeps used: `mcp|MCP|modelcontextprotocol`, `run_pipeline`, `run_phase(`, `aspect`,
`scene`, `agent_tool`, `crop`.




