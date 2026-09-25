# Brandly CLI

<p align="center">
  <img src="assets/banner.png" alt="Brandly CLI Banner" width="100%">
</p>

> **AI product video orchestrator** — add image, video, and sound generation capability to any AI tool (OpenCode, Codex, Qwen Code, Claude Code, etc.) via a CLI and Director agent.

[![PyPI version](https://img.shields.io/pypi/v/brandly-cli.svg)](https://pypi.org/project/brandly-cli/)
[![Python >=3.10](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli)
[![Lint](https://img.shields.io/badge/lint-ruff_clean-brightgreen.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli)
[![CI](https://github.com/Dream-Pixels-Forge/brandly-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli/actions)
[![GitHub stars](https://img.shields.io/github/stars/Dream-Pixels-Forge/brandly-cli?style=social)](https://github.com/Dream-Pixels-Forge/brandly-cli/stargazers)

---

## What is Brandly?

Brandly is an **AI media toolkit for product video**: image, video, and
sound generation plus a real post-production pipeline. It adds these
capabilities to any AI tool (OpenCode, Codex, Qwen Code, Claude Code, etc.)
via a CLI, an agent-callable tool surface, and an MCP server.

**What runs today** (audited 2026-09-25 — gaps tracked in the
[gap register](dev-notes/AUDIT-AGENTIC-PIPELINE.md)):

- **Image generation** via [Agnes AI](https://apihub.agnes-ai.com) (text-to-image, image-to-image)
- **Video generation** via Agnes AI (text-to-video, keyframe-controlled, reference-based)
- **Audio generation** via [MiniMax Audio](https://platform.minimaxi.com) (background music, TTS voiceover)
- **3D Spatial Control** — Blender PlayBlast renderer for spatial reference frames feeding Agnes keyframe/reference modes
- **Shot-by-shot production** — `brandly produce` registers every shot on the production plan, then generates one at a time (retries, resume, canonical `Scene-XX-Shot-X-Y` naming)
- **Assembly & post** — `stitch` (transitions, color grade, G4 `--ratio/--fit`), `captions`, `voice-match` dubbing, `beat-sync`, `thumbnail`, `export-platforms`
- **Scene model + gate** — explicit `scenes.json` manifest and the `brandly gate --scene/--all-scenes` completeness gate (G3)
- **Director orchestration** — `brandly run <id> --execute` advances real phases with per-phase gates; agent/human-driven, not autonomous (G2)
- **Agent tools** — discoverable tool manifest + MCP server; `brandly sync` no longer injects raw provider keys (G1)
- **Credit budgeting** — track spend per phase against a project budget
- **Style presets** — photorealistic, cinematic, editorial, commercial, and documentary
- **Production plan as source of truth** — every generation registers on `docs/plan/production_plan.md`
- **Smaller reference payloads** — large local images auto-convert to webp/jpeg before upload

**Not shipped yet (roadmap — tracked, not claimed):**

- Publish/schedule to TikTok/IG/YouTube — planned, decision-gated (G6)
- Brand-kit enforcement (logo/colour/claim lock) — planned gap
- Performance-metrics ingest — `analyze` is a heuristic predictor; real ingest planned
- Campaign A/B at scale — `batch` exists; variant matrix + scoring loop planned

Run `brandly capabilities` for the machine-readable matrix — the same list
this section is checked against (CI guard: `tests/test_capabilities.py`).

### v0.3.15 New Features + Issue Fixes (#19–#24)

| Fix | Description |
|-----|-------------|
| **Image converter** | `src/brandly_cli/image_convert.py` — large local references auto-shrink to webp/jpeg (JPEG opaque, WebP alpha; `BRANDLY_IMAGE_CONVERT=off` to disable) — 1.7 MB PNG → 410 KB JPEG |
| **`brandly produce` (shot-by-shot)** | New command: registers ALL shots on the production plan first, then generates one at a time with a 60 s wait (1 req/min). No batch/parallel mode; resumable (COMPLETED shots skipped, failures stay PENDING) |
| **Scoped auto-refs (#20)** | `brandly video --no-auto-refs` / `--auto-ref-category <name>` — stop payload bloat + style bleed in multi-look projects |
| **Style follows `--style` (#21)** | `create_video_task` takes `style_preset`; no more hardcoded cinematic suffix on stylised work (e.g. monochrome sumi-e) |
| **Reference import (#23)** | `brandly reference <id> --image <path> [--no-generate]` — adopt client-supplied plates as `primary_reference`, zero credit spend |
| **Visible create errors (#24)** | Failures print `ExceptionType: detail` (no more empty messages); create timeout 60 s → 180 s |
| **Graceful `brandly jobs` (#19)** | 404 degrades to a dim hint (`brandly job-resume <id>`) instead of error spam |
| **Rate-limited `brandly batch`** | Variants submit one at a time (60 s spacing) + style-preset parity; kept as the future batch path when Agnes supports true batch |

### v0.3.12 Bug Fixes

| Fix | Description |
|-----|-------------|
| **Auto credit spend recording** | `brandly video` / `brandly image` now auto-record credits via `CostTracker`; `brandly status` shows real spend — budget gate fires correctly (#18) |
| **Windows Unicode crash fixed** | `cli()` reconfigures stdout/stderr to UTF-8 on Windows; all async Click commands (`jobs`, `edit`, `resize`, `concat`, `audio`, `captions`, `speed`, `batch`, `minimax_*`, `ark_*`) now actually run (#12) |
| **Stitch stderr + no-audio clips** | ffmpeg errors now surface the *tail* of stderr (not the version banner); multi-clip xfade gracefully falls back to video-only when any input lacks an audio stream (#17) |
| **Export ancestor-dir guard** | `brandly export` aborts with a clear message when `--output` is an ancestor of the project dir instead of silently copying nothing (#16) |
| **Agnes 429/400 fixes** | Create-endpoint 429s now back off ≥60 s (respecting the 1 req/min limit); 400 body is surfaced; stale v2.0 tip removed; timeout message points at `job-resume` (#15) |
| **Pipeline no longer a mock** | Director phases dispatch real work — `asset` calls `generate_video`, `audio` calls `generate_music`, `trends` calls `research_trends`, `validate` runs `quality_gate` (#14) |
| **Phase artifact gating** | `brandly approve` now refuses to advance if required artifacts are missing (e.g. approving `asset` with zero clips) (#13) |
| **Root auto-detection** | `_get_root` walks up from cwd looking for `.brandly` marker, preventing doubled-nested project trees when running from inside a project dir (#13) |

### v0.3.9 New Features

| Feature | Description |
|---------|-------------|
| **Blender 3D Spatial Pipeline** | `skills/brandly-3d-spatial/` — PlayBlast + EEVEE fallback renders spatial references for Agnes keyframe/reference modes; Blender version auto-detection via `blender_integration.py` |
| **Resilient 503 Retry** | Video task creation now uses 5 retries with jitter + `Retry-After` header support; prevents transient GPU backend outages from failing the whole pipeline |
| **Spatial Reference System** | `brandly/layout.py` now creates `3d-spatial/{cameras,keyframes,depthmaps,general}/` per project |

### v0.3.7 New Features

| Feature | Description |
|---------|-------------|
| **Quality Gate** | `brandly gate <id> <element>` — anti-slop/anti-drift verification before the next step |
| **AI Visual Review** | Multimodal model scores quality, slop, distortion, drift, and matte backdrop |
| **Auto-Gate** | `brandly reference` and `brandly video` run the gate post-generation (`--no-gate` to skip) |
| **Matte Sheets** | Reference sheets now use a seamless matte mid-grey studio backdrop for clean cutouts |
| **Gate Reports** | Auditable reports written to `.brandly/<project>/docs/tmp/` |

### v0.3.1 New Features

| Feature | Description |
|---------|-------------|
| **Stitch** | Multi-shot video assembly with transitions (fade, dissolve) and color grading |
| **Export Platforms** | Platform-optimized exports for TikTok, Instagram, YouTube, Facebook |
| **Thumbnails** | Keyframe extraction with text overlays |
| **Dubbing** | Multi-language video dubbing via MiniMax TTS |
| **Beat Sync** | Music-reactive editing with beat detection |
| **Auto-Director** | Script-to-video pipeline automation |
| **Trends** | Trending format research database |
| **Analyzer** | Video performance prediction & scoring |
| **Templates** | Reusable project configurations |
| **Webhook** | CI/CD integration with job queue |
| **Sharing** | Cloud export with pluggable providers |

---

## Installation

```bash
pip install brandly-cli
```

### Install Agent Skills

Brandly ships a set of agent skills (camera language, storyboard, production bible,
character/object/vehicle/animal/plant/mecha sheets, 3D spatial, consistency, video generation)
that you can install into any AI tool that supports the `npx skills` protocol:

```bash
npx skills add https://github.com/Dream-Pixels-Forge/brandly-cli/tree/main/skills
```

Available skills (see [skills/README.md](skills/README.md) for details):

| Skill | Purpose |
|-------|---------|
| `brandly-camera` | Hollywood camera language — framing, angles, placement, composition, movement, Rembrandt/butterfly/split lighting |
| `brandly-video-generation` | Master skill — generate AI video & images with prompt engineering |
| `brandly-storyboard` | Plan shot-by-shot visual blueprints |
| `brandly-production-bible` | Single source-of-truth campaign document |
| `brandly-consistency` | Lock visual identity across all shots |
| `brandly-character-sheet` | Character reference sheets |
| `brandly-object-sheet` | Product/object reference sheets |
| `brandly-location-sheet` | Location/set reference sheets |
| `brandly-vehicle-sheet` | Vehicle reference sheets |
| `brandly-mecha-sheet` | Mecha/robot reference sheets |
| `brandly-animal-sheet` | Animal/creature reference sheets |
| `brandly-plant-sheet` | Plant/botanical reference sheets |
| `brandly-3d-spatial` | Blender PlayBlast renderer — spatial reference frames for Agnes keyframe/reference video modes |

### Driving brandly from an AI tool (agent-native surface)

AI coding tools (opencode, Claude Code, Codex, pi, …) should drive brandly through
its tool surface — never by inventing their own ffmpeg/provider calls:

```bash
brandly tools --json     # machine-readable manifest: name, description,
                         # JSON-Schema params, read-only class, backing command
brandly mcp serve        # MCP server over stdio (JSON-RPC 2.0)
```

MCP client config:

```json
{ "mcpServers": { "brandly": { "command": "brandly", "args": ["mcp", "serve"] } } }
```

`brandly init` writes an `AGENTS.md` at the project root (created only if absent —
your file is never overwritten) instructing agents to use this surface.
`brandly sync` no longer writes provider API keys into tool configs by default;
pass `--legacy-provider-keys` only if you deliberately want raw provider access
(which bypasses the pipeline).

#### Orchestrator + subagent workflow (G7)

One orchestrating agent drives the pipeline by dispatching **phase-scoped
subagents** — the contracts and gates are the only shared state:

```bash
brandly plan <project-id> --json        # 1. dispatch source of truth: per phase
                                        #    inputs, outputs, gate, est_cost
brandly run <project-id> --execute --until <phase> --yes   # 4. advance a phase
brandly gate <project-id> --all-scenes  # 3. screen a worker result (deterministic)
```

1. **Read** `brandly plan <id> --json` — each phase carries `inputs[]`,
   `outputs[]`, the deterministic `gate` that verifies it, `next_command`, and
   `est_cost` (budget with `brandly estimate` before dispatching paid work).
2. **Dispatch** one subagent per phase with that contract
   (`brandly director` prints the same table for humans).
3. **Screen** every worker result with its gate — never trust a subagent's
   self-report; `verify_element`/`scenes` run deterministically (`use_ai=False`).
4. **Advance** with `brandly run <id> --execute --until <phase>` — fail-closed:
   a failed phase freezes `current_phase` and exits non-zero.

On failure the run prints (and `plan --json` repeats) a structured
`retry_instruction`: the failing error/verdict, the attempt counter
(`attempts`/`max_attempts`), the exact re-run command, and — once the
3-attempt cap is reached — `escalate: true` with the human escalation command
(`brandly approve <id> <phase>`). Re-dispatch the worker with that reason; the
cap keeps the loop bounded. Cognition can run in parallel, but provider
generation stays single-writer (subagents never fan out paid generation calls
and never publish).

### Configure API Keys

```bash
export AGNES_API_KEY="your-agnes-api-key"
export MINIMAX_API_KEY="your-minimax-api-key"
```

Or create a `.env` file:

```dotenv
AGNES_API_KEY=your_key_here
MINIMAX_API_KEY=your_key_here
AGNES_BASE_URL=https://apihub.agnes-ai.com/v1
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
```

## Quick Start

### 1. Initialize a Project

```bash
brandly init \
  --name "SuperWidget Pro" \
  --idea "A revolutionary widget that organizes your desk with AI" \
  --style cinematic \
  --budget 500 \
  --shots 5 \
  --platforms tiktok instagram youtube
```

### 2. Run the Pipeline

```bash
brandly estimate --style cinematic --shots 5
brandly run <project-id>
brandly approve <project-id> <phase>
brandly director
```

### 3. Generate Media

```bash
brandly image --prompt "product on marble surface" --style-preset cinematic
brandly video <project-id> --prompt "sleek earbuds rotating" --duration 5
brandly music --prompt "upbeat electronic" --duration 30
brandly tts "Welcome to SuperWidget Pro"
```

#### Running image generation externally (isolated context, #75)

All project metadata (plans, generation docs, autosaved media) is written
beneath the selected context root — never inferred. To keep an external
pipeline's working tree clean:

```bash
# Isolated Brandly home (all .brandly/ state lands here, not in the repo):
export ROOT=/tmp/brandly-home          # or: brandly --root /tmp/brandly-home ...

# Write the artifact outside the tree, attach it to an explicit project:
brandly image --prompt "product on marble surface" \
  --output ./out/product.png \
  --project-id superwidget

# No project selected? Pass nothing and run externally — no project records
# are created (the run reports this explicitly instead of falling back to an
# implicit "untitled" project):
brandly image --prompt "hero shot" --output ./out/hero.png --json
```

#### Machine-readable results and explicit outputs (#73)

`--output <path>` is the contract for "put the artifact exactly here": the
provider payload is downloaded/decoded and validated (full decode + format,
width and height probe) before an atomic move, so a failed or truncated
download never leaves a partial or non-image file at the requested path.

`--json` makes the command script-safe: stdout carries exactly one JSON
document and nothing else — callers no longer parse human-readable output to
recover a provider URL.

```bash
brandly image --prompt "hero shot" --output ./out/hero.png --json
```

```json
{
  "status": "success",
  "task_id": "provider-task-handle",
  "provider_url": "https://... (credential query params redacted)",
  "path": "out/hero.png",
  "format": "png",
  "width": 1024,
  "height": 1024,
  "model": "image-model-id",
  "generated_at": "2026-09-24T00:00:00Z",
  "job_id": "job-id (recover with brandly job-poll)"
}
```

Failures exit non-zero with a structured error instead:

```json
{
  "status": "error",
  "error_code": "provider_error | no_image | image_download_failed",
  "error_message": "...",
  "task_id": null,
  "job_id": "job-id"
}
```

Branch on `error_code`, then recover the durable result for that `job_id` with
`brandly job-poll` (#74) instead of re-submitting. Success detection is
payload-driven: URL-only and base64-only provider responses both succeed; only
a response carrying neither payload is reported as `no_image`.


### 4. 3D Spatial References (Optional)

If Blender is installed, generate spatial reference frames for Agnes AI keyframe/reference modes:

```bash
# Detect installed Blender version
python -c "from brandly_cli.blender_integration import detect_blender; v = detect_blender(); print(v)"

# Render spatial references
python skills/brandly-3d-spatial/scripts/playblast_renderer.py \
  --config .brandly/my-project/3d-spatial/cameras/scene.json \
  --output .brandly/my-project/3d-spatial/cameras \
  --mode single

# Extract references for Agnes
python skills/brandly-3d-spatial/scripts/extract_references.py \
  --input .brandly/my-project/3d-spatial/cameras \
  --output .brandly/my-project/3d-spatial/keyframes \
  --strategy first
```

### 5. Export & Share

```bash
brandly export <project-id> --platforms tiktok youtube
brandly thumbnail <project-id>
brandly stitch clip1.mp4 clip2.mp4 --transition fade
brandly voice-match input.mp4 --source en --target es
brandly analyze video.mp4
brandly share output.mp4
```

## CLI Reference

### Project Management

| Command | Description |
|---------|-------------|
| `brandly init` / `brandly start` | Start a new video project |
| `brandly status <id>` | Show project status |
| `brandly list` | List all projects |
| `brandly run <id>` | Run the next pipeline phase |
| `brandly approve <id> <phase>` | Approve a phase and advance |
| `brandly cost <id>` | Show cost summary |

### Media Generation

| Command | Description |
|---------|-------------|
| `brandly image` | Generate an image via Agnes AI (persists a durable job record; recover with `brandly job-poll`) |
| `brandly video <id>` | Generate a video via Agnes AI (with 503 resilience) |
| `brandly music` | Generate background music |
| `brandly tts <text>` | Generate voiceover via TTS |
| `brandly produce <id> --shots shots.json` | Multi-shot film: registers ALL shots on the production plan (source of truth), then generates **one shot at a time** with a 60 s wait (Agnes: 1 request/min). No batch/parallel mode; resumable |
| `brandly job-poll <job-id>` | Poll a durable image-job record; `--output` writes the recovered artifact — never submits a new generation |

### Durable image jobs and retry safety (#74)

`brandly image` writes a job record to `ROOT/.brandly/jobs/<job-id>.json`
before the provider call; terminal state (artifact URL/metadata or failure
reason) is persisted on success/failure. If the process dies — crash,
`--timeout` exceeded, client disconnect — the result is not lost:

```bash
brandly job-poll <job-id> --json                  # status / result_available / path
brandly job-poll <job-id> --output ./recovered.png # write the recovered artifact
```

Polling only reads the durable record, so a disconnected client can never
trigger a duplicate generation. `--max-age` (default 48 h) expires stale
records. For new submissions, retry safety depends on the provider: ones that
honour `X-Client-Request-Id` (Ark/Doubao) allow safe resume; providers
without request-echo support are at-most-once — resubmission may bill again.


Large local reference images are auto-converted to smaller webp/jpeg payloads
before upload (disable with `BRANDLY_IMAGE_CONVERT=off`). Scope auto-injected
references with `brandly video --no-auto-refs` / `--auto-ref-category <name>`,
and adopt client-supplied plates with
`brandly reference <id> --image <path> [--no-generate]`.

### Post-Production

| Command | Description |
|---------|-------------|
| `brandly stitch <clips...>` | Multi-shot video assembly (G4 ratio owner: `--ratio 2.39:1 --fit crop\|pad`) |
| `brandly export <id> --platforms <p>` | Export for specific platforms (`--fit crop\|pad`) |
| `brandly thumbnail <id>` | Generate thumbnails |
| `brandly voice-match <video> --source <lang> --target <lang>` | Dub video |
| `brandly beat-sync <video> <audio>` | Cut video to beats |
| `brandly analyze <video>` | Predict performance metrics |
| `brandly share <file>` | Upload for cloud sharing |

#### Aspect-ratio responsibilities (G4)

| Stage | Ratio behavior |
|-------|----------------|
| Production (`produce`, `video`) | Keeps source aspect — clips are never cropped. `produce --aspect-ratio` is a deprecated alias: it prints a migration notice and defers the crop to assembly |
| Assembly (`stitch --ratio R --fit crop\|pad`) | The single ratio decision: center-crop at source scale, or letterbox/pillarbox with black bars |
| Export (`export-platforms --fit crop\|pad`) | Reuses the assembly filters: crop for feed aspects by default, pad only on request; a source already at the target ratio is a no-op (no double-crop) |

### Intelligence

| Command | Description |
|---------|-------------|
| `brandly trend <category>` | Research trending formats |
| `brandly template list` | List templates |
| `brandly template use <name>` | Create project from template |
| `brandly validate <id>` | Run virality validation |
| `brandly gate <id> [element]` | Verify an element (anti-slop/drift) before the next step |
| `brandly director` | Show Director agent prompt |

### 3D Spatial

| Command | Description |
|---------|-------------|
| (Python API) | `from brandly_cli.blender_integration import detect_blender, is_blender_available` |

---

## Keywords

`ai video generation`, `product video`, `marketing video`, `cli tool`, `agent pipeline`, `multi-agent`, `agentic ai`, `brand video`, `social media video`, `tiktok video`, `youtube video`, `image generation`, `video generation`, `keyframe video`, `reference video`, `blender 3d`, `spatial reference`, `agnes ai`, `minimax tts`, `background music`, `voiceover`, `director agent`, `pipeline orchestration`, `creative ai`, `automated video production`, `product demo`, `commercial`, `advertising`, `content creation`, `shot list`, `storyboard`, `consistency`, `character sheet`, `reference sheet`

---

## License

MIT — Dream Pixels Forge
