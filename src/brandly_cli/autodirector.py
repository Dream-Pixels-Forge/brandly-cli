"""Auto-direct: script-to-video pipeline automation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Script parsing
# ---------------------------------------------------------------------------

def parse_script(script: str) -> list[dict[str, str]]:
    """Parse a script into scenes/segments.

    Splits by paragraph breaks or explicit markers.
    """
    if not script.strip():
        return []

    # Split by double newlines (paragraphs)
    raw_scenes = [s.strip() for s in script.split('\n\n') if s.strip()]

    scenes: list[dict[str, str]] = []
    for i, scene_text in enumerate(raw_scenes, 1):
        # Extract title if present (first line before colon or dash)
        lines = scene_text.split('\n')
        title = ""
        content = scene_text
        if lines and (':' in lines[0] or '-' in lines[0]):
            parts = lines[0].split(':', 1)
            title = parts[0].strip()
            content = scene_text[len(lines[0]):].strip()

        scenes.append({
            "index": i,
            "title": title,
            "text": content,
            "full": scene_text,
        })
    return scenes


# ---------------------------------------------------------------------------
# Auto-direct pipeline
# ---------------------------------------------------------------------------

async def auto_direct(
    project_id: str,
    script: str,
    *,
    style: str = "cinematic",
    shots_per_scene: int = 3,
    root: Path | None = None,
) -> dict[str, Any]:
    """Generate a complete video from a script description.

    Pipeline:
        1. Parse script into scenes
        2. Generate prompts for each scene
        3. Create video segments (stub)
        4. Stitch segments together
        5. Add captions and export

    Args:
        project_id: Project identifier.
        script: The script text.
        style: Visual style preset.
        shots_per_scene: Number of video shots per scene.
        root: Optional project root.

    Returns:
        Dict with pipeline results.
    """
    # Parse script
    scenes = parse_script(script)
    if not scenes:
        return {"error": "Empty or invalid script provided."}

    # In a full implementation, this would:
    # 1. Call video generation API for each scene
    # 2. Generate audio/music
    # 3. Stitch clips together
    # 4. Add captions
    # 5. Export final video

    # For now, return the parsed structure as a demonstration
    return {
        "project_id": project_id,
        "scenes": len(scenes),
        "scenes_parsed": scenes,
        "style": style,
        "shots_per_scene": shots_per_scene,
        "status": "script_parsed",
        "output_path": None,
    }


# ---------------------------------------------------------------------------
# Prompt generation
# ---------------------------------------------------------------------------

def generate_scene_prompt(scene: dict[str, str], style: str, shots: int) -> list[str]:
    """Generate video generation prompts for a scene."""
    prompts: list[str] = []
    scene_text = scene.get("text", "")
    scene_title = scene.get("title", "")

    for i in range(shots):
        prompt = (
            f"{style} style, scene {scene_title}: {scene_text[:100]}... "
            f"Shot {i+1} of {shots}, cinematic camera movement"
        )
        prompts.append(prompt.strip())

    return prompts
