"""Reusable project templates for marketing teams."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATE_REGISTRY: dict[str, dict[str, Any]] = {
    "ig-reel": {
        "style": "ugc",
        "shots": 5,
        "duration": 30,
        "platforms": ["instagram", "tiktok"],
        "budget": 300,
        "prompt_template": "Show {product} in a natural setting with authentic energy...",
        "caption_style": "bold_center",
    },
    "yt-ad": {
        "style": "commercial",
        "shots": 8,
        "duration": 60,
        "platforms": ["youtube"],
        "budget": 500,
        "prompt_template": "Professional product showcase for {product} with clean aesthetics...",
        "caption_style": "professional",
    },
    "tiktok-product": {
        "style": "ugc",
        "shots": 4,
        "duration": 15,
        "platforms": ["tiktok"],
        "budget": 200,
        "prompt_template": "Quick product reveal with trending sound style...",
        "caption_style": "bold_center",
    },
    "youtube-review": {
        "style": "cinematic",
        "shots": 10,
        "duration": 120,
        "platforms": ["youtube"],
        "budget": 600,
        "prompt_template": "In-depth product review with unboxing and demonstration...",
        "caption_style": "professional",
    },
}


# ---------------------------------------------------------------------------
# Template functions
# ---------------------------------------------------------------------------

async def list_templates() -> list[str]:
    """List available template names."""
    return sorted(TEMPLATE_REGISTRY.keys())


async def get_template(name: str) -> dict[str, Any]:
    """Get template configuration by name."""
    if name not in TEMPLATE_REGISTRY:
        raise KeyError(f"Template '{name}' not found. Available: {list(TEMPLATE_REGISTRY)}")
    return TEMPLATE_REGISTRY[name].copy()


async def create_from_template(
    template_name: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create project configuration from template with optional overrides."""
    config = TEMPLATE_REGISTRY[template_name].copy()
    if overrides:
        config.update(overrides)
    return config


async def save_template(
    name: str,
    config: dict[str, Any],
    root: Path | None = None,
) -> None:
    """Save custom template to .brandly/templates/."""
    base = Path(root) if root else Path.cwd()
    templates_dir = base / ".brandly" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    template_file = templates_dir / f"{name}.json"
    template_file.write_text(json.dumps(config, indent=2), encoding="utf-8")


async def delete_template(name: str, root: Path | None = None) -> bool:
    """Delete a custom template. Returns True if deleted, False if not found."""
    base = Path(root) if root else Path.cwd()
    template_file = base / ".brandly" / "templates" / f"{name}.json"

    if template_file.exists():
        template_file.unlink()
        return True
    return False


async def list_custom_templates(root: Path | None = None) -> list[str]:
    """List user-created templates."""
    base = Path(root) if root else Path.cwd()
    templates_dir = base / ".brandly" / "templates"

    if not templates_dir.exists():
        return []

    templates = []
    for f in sorted(templates_dir.glob("*.json")):
        templates.append(f.stem)
    return templates


async def get_custom_template(name: str, root: Path | None = None) -> dict[str, Any]:
    """Load a custom template from disk."""
    base = Path(root) if root else Path.cwd()
    template_file = base / ".brandly" / "templates" / f"{name}.json"

    if not template_file.exists():
        raise KeyError(f"Custom template '{name}' not found")

    return json.loads(template_file.read_text(encoding="utf-8"))
