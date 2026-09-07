# Brandly CLI

<p align="center">
  <img src="assets/banner.png" alt="Brandly CLI Banner" width="100%">
</p>

> **AI product video orchestrator** — add image, video, and sound generation capability to any AI tool (OpenCode, Codex, Qwen Code, Claude Code, etc.) via a CLI and Director agent.

[![PyPI version](https://img.shields.io/pypi/v/brandly-cli.svg)](https://pypi.org/project/brandly-cli/)
[![Python >=3.10](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-303_passing-green.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli)
[![Lint](https://img.shields.io/badge/lint-ruff_clean-brightgreen.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli)
[![CI](https://github.com/Dream-Pixels-Forge/brandly-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Dream-Pixels-Forge/brandly-cli/actions)
[![GitHub stars](https://img.shields.io/github/stars/Dream-Pixels-Forge/brandly-cli?style=social)](https://github.com/Dream-Pixels-Forge/brandly-cli/stargazers)

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

### 4. Export & Share

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
| `brandly image` | Generate an image via Agnes AI |
| `brandly video <id>` | Generate a video via Agnes AI |
| `brandly music` | Generate background music |
| `brandly tts <text>` | Generate voiceover via TTS |

### Post-Production

| Command | Description |
|---------|-------------|
| `brandly stitch <clips...>` | Multi-shot video assembly |
| `brandly export <id> --platforms <p>` | Export for specific platforms |
| `brandly thumbnail <id>` | Generate thumbnails |
| `brandly voice-match <video> --source <lang> --target <lang>` | Dub video |
| `brandly beat-sync <video> <audio>` | Cut video to beats |
| `brandly analyze <video>` | Predict performance metrics |
| `brandly share <file>` | Upload for cloud sharing |

### Intelligence

| Command | Description |
|---------|-------------|
| `brandly trend <category>` | Research trending formats |
| `brandly template list` | List templates |
| `brandly template use <name>` | Create project from template |
| `brandly validate <id>` | Run virality validation |
| `brandly director` | Show Director agent prompt |

---

## License

MIT — Dream Pixels Forge
