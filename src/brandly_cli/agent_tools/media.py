"""Media tools — image generation and model catalog.

Owned by ``brandly-video-generation`` (image generation) — ``list_models``
is a pure utility with no dedicated skill.
"""

from __future__ import annotations

from typing import Any

from brandly_cli.agnes_client import generate_image
from brandly_cli.async_compat import run_async

# ---------------------------------------------------------------------------
# Tool: generate_image
# ---------------------------------------------------------------------------

def _generate_image(
    prompt: str,
    model: str = "agnes-image-2.5-flash",
    size: str = "2K",
    ratio: str = "16:9",
) -> dict[str, Any]:
    """Generate a single Agnes image.  Synchronous wrapper over async."""
    try:
        return run_async(
            generate_image(prompt, model=model, size=size, ratio=ratio)
        )
    except Exception as e:
        return {"error": f"generate_image: {e}"}


# ---------------------------------------------------------------------------
# Tool: list_models
# ---------------------------------------------------------------------------

def _list_models(category: str | None = None) -> dict[str, Any]:
    """List available model IDs across image / video / audio / text."""
    try:
        from brandly_cli.constants import get_all_models

        all_models = get_all_models()
        if category and category in all_models:
            return {"category": category, "models": all_models[category]}
        return all_models
    except Exception as e:
        return {"error": f"list_models: {e}"}


# ---------------------------------------------------------------------------
# Tool registry — media domain
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "generate_image": {
        "handler": _generate_image,
        "schema": {
            "type": "object",
            "title": "Generate Image",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the image to generate.",
                },
                "model": {
                    "type": "string",
                    "default": "agnes-image-2.5-flash",
                    "description": "Agnes image model ID.",
                },
                "size": {
                    "type": "string",
                    "enum": ["1K", "2K", "3K", "4K"],
                    "default": "2K",
                    "description": "Image size tier (1K/2K/3K/4K).",
                },
                "ratio": {
                    "type": "string",
                    "enum": ["1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9"],
                    "default": "16:9",
                    "description": "Aspect ratio (defaults to 21:9 for cinematic style).",
                },
            },
            "required": ["prompt"],
        },
        "description": "Generate a single Agnes image from a text prompt.",
    },
    "list_models": {
        "handler": _list_models,
        "schema": {
            "type": "object",
            "title": "List Models",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["image", "video", "audio", "text"],
                    "description": "Optional category filter.",
                },
            },
        },
        "description": "List available model IDs and metadata across image/video/audio.",
    },
}
