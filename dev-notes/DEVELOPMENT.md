# Brandly CLI — Development Guide

> This file contains development, architecture, and integration details. For end-user documentation, see [README.md](../README.md).

---

## Pipeline Phases

```
init → trends → concept → script → asset → audio → re_edit → validate → publish → done
```

| Phase | Agent | Purpose |
|-------|-------|---------|
| `init` | — | Project initialization |
| `trends` | trends_agent | Research viral formats for the product category |
| `concept` | concept_agent | Create 3 video concepts using STAMP framework |
| `script` | script_agent | Write shot-by-shot script with 8-Layer prompts |
| `asset` | asset_agent | Select models and generate visual assets |
| `audio` | audio_agent | Generate music, SFX, and voiceover |
| `re_edit` | script_agent | Review and refine the script |
| `validate` | validation_agent | Run virality scoring |
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
└── templates/                # Custom saved templates
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

# Run tests with coverage
pytest --cov=src/brandly_cli

# Lint
ruff check src/
ruff check src/ --fix

# Syntax check
python -m py_compile src/brandly_cli/*.py

# Build
python -m build
```

## CI/CD

- **GitHub Actions**: `.github/workflows/ci.yml` runs tests, lint, and syntax checks
- **PyPI Publishing**: `.github/workflows/release.yml` publishes on release via OIDC trusted publishing
- **Pre-commit hooks**: `.pre-commit-config.yaml` with ruff + pytest

### Release checklist

1. Bump **both** `pyproject.toml` `version` and `src/brandly_cli/__about__.py` `__version__` to the same value (CI fails on drift).
2. Update `CHANGELOG.md`.
3. Tag `vX.Y.Z` (must match that version) and publish a GitHub Release — workflow fails on tag/version mismatch.
4. Workflow hard-verifies `https://pypi.org/pypi/brandly-cli/X.Y.Z/json` lists the files (retries ~3 min).

**After publish:** `pip install brandly-cli==X.Y.Z` works as soon as step 4 passes. The project landing page / project-level JSON (`info.version`) is CDN-cached (`max-age=900`) and may still show the previous version for **15–60 minutes**. That lag is not a failed release — confirm via the version URL above or `pip index versions brandly-cli`. Do not re-tag or re-bump for cache lag alone.

## Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `cli.py` | Click command definitions |
| `project_manager.py` | Project CRUD operations |
| `edit.py` | FFmpeg video editing |
| `stitch.py` | Multi-shot assembly |
| `export_platforms.py` | Platform-specific exports |
| `thumbnails.py` | Keyframe extraction |
| `dubbing.py` | Multi-language dubbing |
| `beat_sync.py` | Music-reactive editing |
| `autodirector.py` | Script-to-video pipeline |
| `trends.py` | Trend research database |
| `analyzer.py` | Performance prediction |
| `templates.py` | Project templates |
| `webhook.py` | CI/CD webhook server |
| `sharing.py` | Cloud export providers |

### API Providers

| Provider | Purpose |
|----------|---------|
| `agnes_client.py` | Image + video generation |
| `ark_client.py` | BytePlus Ark (Seedream/Seedance) |
| `minimax_client.py` | Music + TTS |

### Key Dependencies

- `click` — CLI framework
- `pydantic` — Data validation
- `httpx` — Async HTTP client
- `rich` — Terminal UI
- `pillow` — Image processing
- `pytest` / `pytest-asyncio` — Testing

## License

MIT — Dream Pixels Forge
