# Brandly CLI

<p align="center">
  <img src="assets/banner.png" alt="Brandly CLI Banner" width="100%">
</p>

> **AI product video orchestrator** — plan, generate, and publish professional product videos with AI. Works from the terminal, or from any AI assistant (OpenCode, Codex, Qwen Code, Claude Code, Cursor, …) through agent tools and an MCP server.

[![PyPI version](https://img.shields.io/pypi/v/brandly-cli.svg)](https://pypi.org/project/brandly-cli/)
[![Python >=3.10](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli)
[![Lint](https://img.shields.io/badge/lint-ruff_clean-brightgreen.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli)
[![CI](https://github.com/Dream-Pixels-Forge/brandly-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli/actions)
[![GitHub stars](https://github.com/Dream-Pixels-Forge/brandly-cli?style=social)](https://github.com/Dream-Pixels-Forge/brandly-cli/stargazers)

---

## What is Brandly?

Brandly turns a product idea into a finished video. You describe the product; Brandly plans the shots, generates the footage, checks the quality, and exports it for the platforms you want — TikTok, Instagram, YouTube, or a plain MP4.

Everything runs from one command, `brandly`, with **83 commands** behind it. You never have to use all of them: the quick start below uses five.

### What you can do

| Capability | What it means |
|------------|---------------|
| **Generate images** | Text-to-image and image-to-image via Agnes AI (also MiniMax and BytePlus Seedream) |
| **Generate video** | Text-to-video, single clips or multi-shot films with consistent characters and products |
| **Generate audio** | Background music, voiceovers (text-to-speech), dubbing into other languages |
| **Plan like a director** | The pipeline researches trends, writes a concept, then breaks it into shots — each shot has camera, lighting, and style direction |
| **Check quality automatically** | Every generated clip is measured (did it come back the length you asked for?) and vision-judged for drift and slop |
| **Assemble and export** | Stitch clips, add captions, sync to music, export per platform (9:16, 1:1, 16:9) |
| **Resume anything** | A crashed run picks up where it left off — state lives on disk, not in memory |
| **Publish** | Schedule posts to TikTok/Instagram/YouTube (dry-run first, your credentials, stored locally) |
| **Visual editor** | `brandly timeline` opens a browser-based timeline to see and arrange everything |

### Who is it for?

- **Marketers and creators** — make product videos without a production team
- **Developers** — drive video generation from your own apps or agents (CLI, agent tools, MCP server)
- **AI enthusiasts** — orchestrate image + video + audio models in one workflow

---

## Quick start (5 minutes)

### 1. Install

```bash
pip install brandly-cli
```

### 2. Get an API key

1. Sign up at [Agnes AI](https://apihub.agnes-ai.com)
2. Copy your API key
3. Set it as an environment variable:

```bash
export AGNES_API_KEY="your_key_here"
# add to ~/.bashrc or ~/.zshrc to make it permanent
```

Or let Brandly sync your existing AI-tool configs automatically:

```bash
brandly sync
```

### 3. Create your first project

```bash
brandly init -n "My Product" -i "A sleek wireless charger that doubles as a desk lamp"
```

That's it — one command, one idea. Add `-s cinematic` for a cinematic style or `-b 200` to set a credit budget when you're ready for more control.

### 4. Run the pipeline

```bash
# let the pipeline run phase by phase (stops for your approval at human gates)
brandly run <project_id> --execute --until publish
```

Or run it one phase at a time — `script` writes the shot list, `asset` generates the shots, `validate` checks quality, `publish` exports.

### 5. See the results

```bash
brandly timeline <project_id>   # visual timeline editor in your browser
brandly status <project_id>     # text status: what exists, what's next
```

---

## How it works

Brandly runs your project through a fixed sequence of phases. Each phase has a clear job, and each one refuses to continue on failure — so a broken step never quietly produces bad footage downstream.

```text
init → trends → concept → script → asset → audio → re_edit → validate → publish
```

| Phase | What it does | What you get |
|-------|--------------|--------------|
| **init** | Records your product, style, and budget | A project folder on disk |
| **trends** | Researches current video formats for your style | `docs/plan/trends.md` |
| **concept** | Derives the creative concept from your brief | `docs/plan/concept.md` |
| **script** | Breaks the concept into shots with beat structure | `shots.json` — the shot list |
| **asset** | Generates each shot (reference image first, then clips) | Clips on disk, one file per shot |
| **audio** | Generates background music sized to the film | `production/<id>/audio/music.mp3` |
| **re_edit** | Mixes the music into the final cut | `final.mp4` |
| **validate** | Scores the finished video for virality | A validation report |
| **publish** | Exports per platform and schedules posts | Platform-ready files + scheduled posts |

You approve at the gates (`brandly approve <id> <phase>`); Brandly handles the rest. Everything it does is visible: `brandly plan <id> --json` shows each phase's inputs and outputs, `brandly cost <id>` shows what was spent, `brandly scenes <id>` shows the shot manifest.

---

## Two ways to work

### Creators: you drive, step by step

```bash
brandly init -n "Product Name" -i "Brief description" -s cinematic
brandly status <id>            # review the plan
brandly approve <id> script    # approve the shot list
brandly run <id> --execute --until asset     # generate shots (resumable)
brandly gate <id> --all-scenes               # quality check
brandly run <id> --execute --until publish   # assemble & export
```

## Driving brandly from an AI tool

Brandly exposes **22 agent-callable tools** through its MCP server — the same operations as the CLI, packaged for AI tools:

```bash
brandly mcp serve              # start the MCP server
brandly tools --json           # list all 22 tools with read-only flags
brandly tools call produce --project_id <id> --shots 5
```

Ten tools are read-only (safe for an agent to call without asking): `list_projects`, `get_project`, `list_jobs`, `list_models`, `get_timeline`, `run_gate`, `plan`, `status`, `progress`, `estimate`. Twelve write state — including `approve`, which stays a human gate on purpose: an AI can *ask* for approval, but a person decides.

For a full walkthrough of driving Brandly from an AI tool:

```bash
brandly director               # print the Director prompt for your AI tool
```

---

## Command cheat sheet

83 commands, grouped by what you're trying to do. Run `brandly <command> --help` for any of them.

### Projects

```bash
brandly init -n "Name" -i "Idea" -s cinematic -b 500   # new project
brandly list                                           # all projects
brandly status <id>                                    # what exists, what's next
brandly pause <id> / brandly resume <id>               # pause and resume
brandly cancel <id>                                    # cancel a project
brandly template / brandly template-list               # reusable project templates
```

### The pipeline

```bash
brandly run <id> --execute --until produce             # run phase by phase
brandly run <id> --execute --only shot-03 shot-07      # regenerate specific shots
brandly approve <id> <phase>                           # human gate approval
brandly plan <id> --json                               # phase contracts: inputs/outputs
brandly scenes <id> --json                             # the shot manifest
brandly script <id>                                    # validate beat completeness
brandly produce <id> --shots shots.json --interval 60  # manual shot-by-shot run
```

### Generation

```bash
brandly video <id> -p "prompt" --style commercial      # single video clip
brandly image <id> -p "prompt"                         # single image
brandly reference <id>                                 # the primary reference image
brandly music <id>                                     # background music
brandly tts <id>                                       # voiceover
brandly batch <id>                                     # variants of a base prompt
brandly storyboard <id>                                # keyframes for each shot
brandly ark-video / minimax-video                      # other providers
```

### Quality

```bash
brandly gate <id> --all-scenes                         # all scenes, checked
brandly gate <id> --element ./clip.mp4 --ref ./ref.png # one element vs its reference
brandly gate-drift <id>                                # cross-shot prompt drift check
brandly validate <id>                                  # virality scoring
brandly analyze <id> / brandly analyze-project <id>    # performance prediction
```

### Post-production

```bash
brandly assemble <id>                                  # assemble the final film
brandly stitch c1.mp4 c2.mp4 --output final.mp4        # stitch clips
brandly captions <id>                                  # burned-in subtitles
brandly beat-sync <video> <music>                      # cut to the beat
brandly voice-match <video> --target es                # dub to another language
brandly mux <video>                                    # mix narration/music into a video
brandly thumbnail <id> --style cinematic               # thumbnails
```

### Export & publish

```bash
brandly export <id> --platforms tiktok,instagram,youtube   # platform renders
brandly export-platforms <id>                              # 9:16 / 1:1 / 16:9 formats
brandly publish <id> --dry-run                             # preview the posts
brandly publish <id> --platforms tiktok,instagram          # schedule them
brandly config set tiktok <token>                          # store credentials
brandly share <id>                                         # upload to cloud for sharing
```

### Money & limits

```bash
brandly estimate --style cinematic --shots 8           # cost before you start
brandly estimate --target-duration 120                 # quota-aware plan (warns + multi-day split)
brandly cost <id> --breakdown                          # what each phase spent
brandly record-cost <id> --phase asset --credits 40    # record actual spend
brandly rate-limits                                    # provider rate limits
brandly models / brandly model <name>                  # what models are available
```

### Media utilities

```bash
brandly probe <video>          # video metadata
brandly resize <video>         # resize / change aspect ratio
brandly speed <video>          # playback speed
brandly edit <video>           # trim to a segment
brandly concat a.mp4 b.mp4     # concatenate
brandly audio <video>          # extract the audio track
brandly optimize-refs <img>    # split a large reference into small + HQ pair
```

### Tools & integration

```bash
brandly mcp serve              # MCP server for AI tools
brandly tools --json           # the 22-tool agent surface
brandly director               # the Director prompt
brandly capabilities           # capability map per persona
brandly sync                   # auto-detect AI-tool configs
brandly webhook                # webhook server for CI/CD
brandly team                   # multi-user collaboration
brandly report                 # report a bug or request a feature
```

---

## Built-in safety

Brandly is designed to fail loudly and spend carefully:

- **Human gates** — the pipeline stops at phase boundaries for your approval. `approve` is always a person's decision.
- **Fail-closed phases** — a failed step freezes the pipeline and exits non-zero; nothing downstream continues on broken input.
- **Measured truth** — every returned clip is measured against what was requested. A 5-second take for a 12-second request is never silently marked OK: it triggers a continuation take, or ships honestly marked short.
- **Cost awareness** — `brandly estimate` previews the credit cost before you start; quota warnings propose a multi-day schedule when a plan would exceed your daily limit.
- **Fail-honest quality** — when a quality check couldn't actually run (no API key, AI unavailable), results are marked `UNVERIFIED` — never passed as verified.
- **Dry-run publishing** — `brandly publish --dry-run` shows exactly what would be posted before anything is scheduled.
- **Credentials stay local** — provider tokens live in your local config, never in the project or the repo.

---

## Styles & references

### Styles

| Style | Best for |
|-------|----------|
| cinematic | Storytelling, brand films |
| commercial | Product demos, ads |
| ugc | TikTok/Reels native feel |
| montage | Fast-paced showcase |
| continuous | One-take style |
| unboxing | Product reveals |
| lifestyle | In-context usage |

### Reference images (consistency across shots)

Register your character and product references once, and every shot stays consistent:

```bash
brandly reference <id> --image char.png --subject-type character
brandly reference <id> --image prop.png --subject-type prop
```

For keyframe-controlled clips (start and end frames fixed):

```bash
brandly video <id> -p "transition" --mode keyframe --first-frame start.png --last-frame end.png
```

---

## Monitoring & debugging

```bash
brandly status <id>            # project dashboard
brandly progress <id>          # detailed phase progress
brandly cost <id> --breakdown  # spending
brandly rate-limits            # provider rate limits & daily quota
brandly jobs                   # recent API jobs
brandly job-resume <video_id>  # recover a crashed job
brandly job-poll <video_id>    # poll a job to completion
brandly timeline <id> --port 8765   # visual editor
brandly metrics                # platform metrics ingest
brandly brand <id>             # brand-kit enforcement (logo/colour/claim lock)
```

---

## Configuration

```bash
brandly config show            # view current config
brandly config set tiktok "access_token=..."
brandly config set instagram "access_token=..."
brandly config set youtube "client_id=... client_secret=..."
brandly memory show            # your preferences (budget, defaults)
```

Environment variables:

```bash
export AGNES_API_KEY="..."          # required for Agnes video/image
export BRANDLY_IMAGE_CONVERT=off    # disable automatic image compression
export BRANDLY_WEB_PORT=8765        # timeline editor port
```

---

## For developers

<details>
<summary><strong>Architecture, pipeline internals, and the provider seam</strong></summary>

### State model

All state lives in `.brandly/<project>/` on disk — disk is the only shared state, so runs are resumable and inspectable:

```text
.brandly/<project>/
├── project.json        # product, style, budget, phase state
├── shots.json          # canonical shot list (produce + gate-drift resolve this)
├── cost.json           # per-phase spend
├── scenes.json         # scene manifest with beats and durations
├── docs/plan/          # trends.md, concept.md
├── pre-production/     # reference plates, storyboards
└── production/         # clips, audio, final.mp4
```

### Pipeline guarantees

- Each phase is fail-closed: failure freezes `current_phase` and exits non-zero.
- Phase handoffs are explicit contracts — `brandly plan <id> --json` lists every phase's inputs, outputs, and gate command (`PHASE_HANDOFF_SPECS`).
- Shot generation is rate-limited (1 request/minute by default) with durable job polling.

### Key modules

| Module | Responsibility |
|--------|----------------|
| `agnes_client.py` | Agnes AI HTTP client (retry, backoff, 503 handling) |
| `shot_runner.py` | Resumable shot-by-shot generation, clip measurement, continuation takes |
| `scenes.py` | Scene manifest + beat validation (`REQUIRED_BEATS`, `BEAT_DURATIONS`) |
| `quality_gate.py` | Deterministic + AI-vision verification (`UNVERIFIED` is never `PASS`) |
| `director.py` | Director prompt + orchestration plan |
| `stitch.py` | FFmpeg assembly (transitions, ratio, color) |
| `export_platforms.py` | Platform-specific renders (9:16, 1:1, 16:9) |
| `cost_tracker.py` | Per-phase budgeting + daily quota tracking |
| `agent_surface.py` | The 22-tool MCP surface (tool surface = CLI surface) |
| `video_backend.py` | `VideoBackend` protocol — pluggable video providers |

### Provider seam

Video generation depends on a `VideoBackend` protocol, not a concrete client — Agnes is one implementation. Adding another provider:

```python
from brandly_cli.video_backend import VideoBackend, VideoBackendCapabilities

class MyBackend(VideoBackend):
    def capabilities(self) -> VideoBackendCapabilities: ...
    async def submit(self, ...) -> ...: ...
    async def poll(self, ...) -> ...: ...
    async def fetch(self, ...) -> ...: ...
```

Then pass `video_backend=MyBackend()` in `RunnerConfig`.

</details>

---

## Demos

![Studio preview](assets/studio-preview.png)

Producer videos: [F1tr08UeHLs](https://youtu.be/F1tr08UeHLs) · [7lNt1Y8tAzo](https://youtu.be/7lNt1Y8tAzo)

---

## Roadmap

- ✅ Publish/schedule — supported via `brandly publish` (dry-run, multi-platform posts, stored credentials)
- ✅ Quality gates — per-scene and element checks via `brandly gate`
- ✅ Studio shell — visual timeline editor via `brandly timeline`
- ✅ Agent surface — 22 tools via MCP (`brandly tools --json`)
- ✅ Document chain — trends → concept → script is a real, fail-closed chain
- ⏳ Additional video backends — the `VideoBackend` seam is ready; more providers welcome

---

## Development

```bash
pip install -e ".[dev]"       # dev dependencies
make test                     # full suite (Python + web contracts)
make lint                     # ruff + oxlint + mypy + import-linter
cd web && npm run dev         # web UI development
pip wheel . -w dist/          # build the wheel
```

Pipeline governance: [AUDIT-AGENTIC-PIPELINE.md](dev-notes/AUDIT-AGENTIC-PIPELINE.md) is the single source of truth for open gaps.

---

## Star this repo

If Brandly helps you create better product videos, please consider starring the repository on GitHub — it helps others discover the project and motivates continued development.

[![GitHub stars](https://github.com/Dream-Pixels-Forge/brandly-cli?style=social)](https://github.com/Dream-Pixels-Forge/brandly-cli/stargazers)

---

## License

MIT — Dream Pixels Forge
