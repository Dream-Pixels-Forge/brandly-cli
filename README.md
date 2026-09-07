# Brandly CLI

> **AI product video orchestrator** — add image, video, and sound generation capability to any AI tool (OpenCode, Codex, Qwen Code, Claude Code, etc.) via a CLI and Director agent.

[![PyPI version](https://img.shields.io/pypi/v/brandly-cli.svg)](https://pypi.org/project/brandly-cli/)
[![Python >=3.10](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is Brandly?

Brandly is an **autonomous video production pipeline** that turns product ideas into platform-ready marketing videos. It provides:

- **Image generation** via [Agnes AI](https://apihub.agnes-ai.com) (text-to-image, image-to-image)
- **Video generation** via Agnes AI (text-to-video, keyframe-controlled, reference-based)
- **Audio generation** via [MiniMax Audio](https://platform.minimaxi.com) (background music, TTS voiceover)
- **Multi-agent pipeline** — automated workflow from idea → trends → concept → script → assets → audio → validate → publish
- **Director orchestrator** — an autonomous agent that guides the entire production process
- **Credit budgeting** — track spend per phase against a project budget
- **Style presets** — avoid AI slop with photorealistic, cinematic, editorial, commercial, and documentary presets

## Installation

```bash
pip install brandly-cli
```

### Configure API Keys

```bash
# Agnes AI (image + video generation)
export AGNES_API_KEY="your-agnes-api-key"

# MiniMax Audio (music + TTS)
export MINIMAX_API_KEY="your-minimax-api-key"
```

Or create a `.env` file in your project root:

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
# Check cost estimate first
brandly estimate --style cinematic --shots 5

# Run each phase
brandly run <project-id>        # Start the current phase
brandly approve <project-id> <phase>  # Approve and advance

# Or run the full pipeline at once
brandly director                # Shows Director prompt for AI tools
```

### 3. Generate Media Directly

```bash
# Image generation
brandly image --prompt "product on marble surface, studio lighting" \
              --style-preset cinematic

# Video generation
brandly video <project-id> --prompt "sleek wireless earbuds rotating" \
               --duration 5 --wait

# Audio generation
brandly music --prompt "upbeat electronic background music" --duration 30
brandly tts "Welcome to SuperWidget Pro"
```

### 4. Export

```bash
brandly export <project-id>
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `brandly init` / `brandly start` | Start a new video project |
| `brandly status <id>` | Show project status |
| `brandly list` | List all projects |
| `brandly run <id>` | Run the next pipeline phase |
| `brandly approve <id> <phase>` | Approve a phase and advance |
| `brandly estimate` | Estimate credit cost |
| `brandly image` | Generate an image via Agnes AI |
| `brandly video <id>` | Generate a video via Agnes AI |
| `brandly music` | Generate background music via MiniMax Audio |
| `brandly tts <text>` | Generate voiceover via TTS |
| `brandly voices` | List available TTS voices |
| `brandly validate <id>` | Run virality validation |
| `brandly progress <id>` | Show detailed progress |
| `brandly export <id>` | Export project artifacts |
| `brandly cost <id>` | Show cost summary |
| `brandly record-cost <id> <phase> <action> <credits>` | Record credit spend |
| `brandly memory` | View/update user preferences |
| `brandly cancel / pause / resume <id>` | Control project state |
| `brandly director` | Show Director agent prompt |
| `brandly config` | Show configuration |

## Pipeline Phases

```
init → trends → concept → script → asset → audio → re_edit → validate → publish → done
```

Each phase has a corresponding agent prompt that defines the task for the AI orchestrator:

| Phase | Agent | Purpose |
|-------|-------|---------|
| `init` | — | Project initialization |
| `trends` | trends_agent | Research viral formats for the product category |
| `concept` | concept_agent | Create 3 video concepts using STAMP framework |
| `script` | script_agent | Write shot-by-shot script with 8-Layer prompts |
| `asset` | asset_agent | Select models and generate visual assets |
| `audio` | audio_agent | Generate music, SFX, and voiceover |
| `re_edit` | script_agent | Review and refine the script |
| `validate` | validation_agent | Run virality scoring (requires Higgsfield MCP) |
| `publish` | publish_agent | Generate platform-specific metadata |
| `done` | — | Pipeline complete |

## Video Styles

| Style | Credits (base) | Best For |
|-------|---------------|----------|
| `cinematic` | 250 | Premium brand stories |
| `ugc` | 150 | User-generated content style |
| `montage` | 200 | Fast-paced highlight reels |
| `multi_shot` | 300 | Complex multi-scene videos |
| `continuous` | 200 | Single-take seamless shots |
| `unboxing` | 180 | Product reveal videos |
| `lifestyle` | 170 | Contextual product usage |
| `collage_motion_graphic` | 350 | Animated collage sequences |
| `brand_short_video` | 280 | Short-form brand content |
| `explainer_video` | 400 | Educational/instructional |

## Style Presets (Avoid AI Slop)

| Preset | Description |
|--------|-------------|
| `photorealistic` | Camera/lens/grain, natural skin texture |
| `editorial` | Magazine look, studio lighting |
| `cinematic` | Anamorphic, film grade, teal & orange |
| `commercial` | Product photography, clean studio |
| `documentary` | Photojournalism, available light |

## Director Mode

The **Director** is an autonomous orchestrator agent. When invoked by an AI tool, it:

1. Gathers product info (name, idea, style, budget, platforms)
2. Creates a project via `brandly init`
3. Runs the pipeline phase by phase
4. Checks virality, manages budget, and exports final assets

To use it with any AI tool, copy the output of:

```bash
brandly director
```

## Project Structure

```
.brandly/
├── projects/
│   └── {project-id}/
│       ├── project.json      # Project state
│       ├── cost.json         # Credit spend log
│       └── artifacts/
│           └── {phase}/      # Phase outputs (.md, .json)
├── user-preferences.json     # Liked/disliked hooks, style prefs
```

Generated media is stored in:
- `imagen/{project-id}/` — generated images
- `videgen/{project-id}/` — generated videos
- `audgen/{project-id}/` — generated audio

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Build
python -m build
```

## Integration with AI Tools

### OpenCode

Add to `.opencode/package.json`:
```json
{ "dependencies": { "brandly": "github:Dream-Pixels-Forge/brandly-plugin" } }
```

Register in `opencode.json`:
```json
{ "$schema": "https://opencode.ai/config.json", "plugin": ["brandly"] }
```

### Codex / Qwen Code / Claude Code

Use the CLI directly — all commands are designed to be called by agent subprocesses. The Director prompt provides the orchestration logic.

## License

MIT — Dream Pixels Forge
