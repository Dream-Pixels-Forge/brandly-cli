# SPEC — brandly-cli Architecture Specification

> **Project:** brandly-cli  
> **Version:** 0.2.0  
> **Date:** 2026-09-07

---

## 1. Architecture Overview

brandly-cli is a Python CLI tool that orchestrates AI-generated video production. It integrates three AI providers (Agnes AI, BytePlus Ark, MiniMax) into a unified pipeline with credit budgeting, style presets, and reference image anchoring.

### 1.1 Core Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Click** for CLI framework | Mature, well-documented, supports `--root` option for testing |
| **Pydantic v2** for models | Type-safe, supports `extra="allow"` for forward compatibility |
| **Async httpx** for API calls | Consistent async pattern across all providers |
| **File-based project state** | No database dependency; projects are directories of JSON + media |
| **Root-aware path resolution** | `--root` / `ROOT` env var enables testing and multi-project workflows |
| **Style presets with negative prompts** | Reduces "AI slop" in generated images/video |
| **Reference image anchoring** | Enables character/object consistency across generations |

### 1.2 Data Flow

```
User input (CLI args)
    ↓
Click command handler
    ↓
[Optional] Load project from .brandly/projects/{id}/project.json
    ↓
Build prompt (style preset + video_prompts templates)
    ↓
API call (Agnes / Ark / MiniMax)
    ↓
Save artifact (.brandly/projects/{id}/artifacts/{type}/)
    ↓
Write generation doc (.brandly/projects/{id}/docs/)
    ↓
Update project state (phase progress, cost)
    ↓
Output (table / JSON)
```

### 1.3 Project Layout

```
.brandly/
├── projects/
│   └── {project-id}/
│       ├── project.json        # Project state (Pydantic model)
│       ├── cost.json           # Credit spend tracking
│       ├── artifacts/
│       │   ├── images/         # Generated images
│       │   ├── videos/         # Generated videos
│       │   ├── audio/          # Generated music/TTS
│       │   └── docs/           # Generation plans + docs
│       └── export/             # Final export (brandly export)
└── user-preferences.json       # User likes/dislikes
```

---

## 2. Pipeline Phases

| Phase | Description | Commands |
|-------|-------------|----------|
| `init` | Create project, set style/budget/shots | `brandly init` |
| `trends` | Research trending formats | `brandly run` (agent-driven) |
| `concept` | Generate creative concepts | `brandly run` (agent-driven) |
| `script` | Write shot-by-shot script | `brandly run` (agent-driven) |
| `asset` | Generate images + videos | `brandly image`, `brandly video` |
| `audio` | Generate music + TTS | `brandly music`, `brandly tts` |
| `re_edit` | Trim, concat, resize videos | `brandly edit`, `brandly concat`, etc. |
| `validate` | Virality scoring | `brandly validate` |
| `publish` | Export + deploy | `brandly export` |
| `done` | Pipeline complete | — |

---

## 3. API Provider Interface

### 3.1 Agnes AI
- **Base URL:** `https://apihub.agnes-ai.com/v1`
- **Auth:** Bearer token via `AGNES_API_KEY`
- **Image endpoint:** `/generation/image/generate`
- **Video endpoint:** `/generation/video/create`
- **Status endpoint:** `/generation/video/{id}`
- **Features:** text-to-image, img2img, style transfer, text-to-video, img2video

### 3.2 BytePlus Ark
- **Base URL:** `https://ark.cn-beijing.volces.com/api/v3`
- **Auth:** Bearer token via `ARK_API_KEY`
- **Image model:** `seedream-4.0` / `seedream-3.5`
- **Video model:** `seedance-1.0-t2v` / `seedance-1.0-i2v`
- **Features:** text-to-image, text-to-video, image-to-video

### 3.3 MiniMax
- **Base URL:** `https://api.minimaxi.com/v1`
- **Auth:** Bearer token via `MINIMAX_API_KEY`
- **Image endpoint:** `/v1/image_generation`
- **Video endpoint:** `/v1/video_generation`
- **Music endpoint:** `/v1/music_generation`
- **TTS endpoint:** `/v1/t2a_v2`
- **Features:** text-to-image, text-to-video, image-to-video, music gen, TTS

---

## 4. Style Preset System

| Preset | Prompt Suffix | Negative Prompt | Use Case |
|--------|--------------|-----------------|----------|
| `photorealistic` | Sony A7IV, 85mm lens, natural skin texture | AI generated, smooth plastic skin | Product photos, portraits |
| `editorial` | Vogue magazine, high fashion, dramatic lighting | Cartoon, anime, 3D render | Fashion, luxury campaigns |
| `cinematic` | Anamorphic lens flares, 2.39:1, film grain | Airbrushed, oversaturated | Storytelling, trailers |
| `commercial` | Clean product focus, studio lighting | Distracting elements, clutter | Product ads, demos |
| `documentary` | Handheld camera, natural light, authentic | Studio lighting, perfect composition | Real-world, raw footage |

---

## 5. Cost Model

### 5.1 Base Costs by Style
| Style | Base Cost (credits) |
|-------|---------------------|
| cinematic | 250 |
| ugc | 150 |
| montage | 200 |
| multi_shot | 300 |
| continuous | 200 |
| unboxing | 180 |
| lifestyle | 170 |
| collage_motion_graphic | 350 |
| brand_short_video | 280 |
| explainer_video | 400 |

### 5.2 Per-Shot Extra Cost
| Shots | Extra Cost |
|-------|-----------|
| 3 | 0 |
| 4 | 15 |
| 5 | 30 |
| 6 | 50 |
| 7 | 75 |
| 8 | 100 |
| 9 | 140 |
| 10 | 180 |

### 5.3 Phase Cost Estimates
| Phase | Estimate (credits) |
|-------|-------------------|
| init | 0 |
| trends | 10 |
| concept | 42 |
| script | 56 |
| asset | 70 |
| audio | 42 |
| re_edit | 20 |
| validate | 10 |
| publish | 5 |

---

## 6. CLI Command Reference

### 6.1 Project Management
| Command | Description |
|---------|-------------|
| `brandly init` | Create a new project |
| `brandly list` | List all projects |
| `brandly status <id>` | Show project status |
| `brandly progress <id>` | Show pipeline progress |
| `brandly run <id>` | Run next phase |
| `brandly approve <id> <phase>` | Approve phase and advance |
| `brandly pause <id>` | Pause a project |
| `brandly resume <id>` | Resume a paused project |
| `brandly cancel <id>` | Cancel a project |
| `brandly export <id>` | Export project artifacts |

### 6.2 Generation
| Command | Description |
|---------|-------------|
| `brandly image` | Generate image via Agnes AI |
| `brandly video <id>` | Generate video via Agnes AI |
| `brandly ark-image` | Generate image via BytePlus Ark |
| `brandly ark-video <id>` | Generate video via BytePlus Ark |
| `brandly minimax-image` | Generate image via MiniMax |
| `brandly minimax-video <id>` | Generate video via MiniMax |
| `brandly reference <id>` | Generate reference image for consistency |
| `brandly prompt` | Generate cinematic video prompt |
| `brandly music` | Generate background music |
| `brandly tts` | Generate voiceover |
| `brandly captions` | Add subtitles to video |

### 6.3 Editing
| Command | Description |
|---------|-------------|
| `brandly edit` | Trim video |
| `brandly resize` | Resize video |
| `brandly concat` | Concatenate videos |
| `brandly speed` | Change playback speed |
| `brandly audio` | Extract audio track |
| `brandly analyze` | Get video metadata |

### 6.4 Utilities
| Command | Description |
|---------|-------------|
| `brandly config` | Show configuration |
| `brandly estimate` | Estimate credit cost |
| `brandly cost <id>` | Show cost summary |
| `brandly record-cost` | Record credit spend |
| `brandly models` | List available models |
| `brandly model` | Show model details |
| `brandly voices` | List TTS voices |
| `brandly memory` | View/update preferences |
| `brandly sync` | Sync API keys to tool configs |
| `brandly director` | Show Director prompt |
| `brandly jobs` | List recent jobs |
| `brandly batch` | Generate video variants |
| `brandly compare` | Compare project assets |

### 6.5 Provider-Specific
| Command | Description |
|---------|-------------|
| `brandly ark-jobs` | List Ark video jobs |
| `brandly ark-cancel <id>` | Cancel Ark job |
| `brandly minimax-jobs` | List MiniMax jobs |
| `brandly job-cancel <id>` | Cancel pending job |
| `brandly job-resume <id>` | Poll and wait for job |

---

## 7. Error Handling

All API clients implement:
- **Exponential backoff** for 429 (rate limit) and 503 (server error)
- **Permanent error detection** — non-retryable errors (4xx, model_not_found) are raised immediately
- **Graceful fallbacks** — clear error messages with actionable next steps
- **Budget gates** — `CostTracker` prevents spending beyond project budget

---

*Specification v0.2.0 — brandly-cli is aligned with DPF standards.*
