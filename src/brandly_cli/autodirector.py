"""Auto-direct: script parsing and prompt-generation utilities.

The old ``auto_direct`` pipeline stub was deleted in G2 PR D (audit F3/F4) —
the real pipeline is ``brandly run --execute`` (``Director.run_pipeline`` in
``cmd/production.py``).  The utilities below are pure, tested helpers.
"""

from __future__ import annotations

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
            "index": str(i),
            "title": title,
            "text": content,
            "full": scene_text,
        })
    return scenes


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
