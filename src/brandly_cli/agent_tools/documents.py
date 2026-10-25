""".brandly document tools — production bible and screenplay.

The bible is written *first* (before cast/wardrobe/location/sound) so every
downstream tool anchors to the script.  Owned by
``brandly-production-bible`` (bible) and ``brandly-screenplay-architect``
(screenplay).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brandly_cli.io import now_iso, write_json
from brandly_cli.layout import docs_dir
from brandly_cli.types import BibleContent, ScreenplayContent

# ---------------------------------------------------------------------------
# Tool: write_bible / read_bible
# ---------------------------------------------------------------------------

def _write_bible(
    project_id: str,
    title: str,
    logline: str,
    tone: str = "",
    genre: str = "",
    visual_style: str = "cinematic",
    color_palette: str = "",
    characters: list[dict[str, Any]] | None = None,
    locations: list[dict[str, Any]] | None = None,
    props: list[dict[str, Any]] | None = None,
    wardrobe_notes: str = "",
    sound_notes: str = "",
    camera_notes: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Write the production bible to ``.brandly/{id}/docs/bible/``."""
    try:
        bible = BibleContent(
            project_id=project_id,
            title=title,
            logline=logline,
            tone=tone,
            genre=genre,
            visual_style=visual_style,
            color_palette=color_palette,
            characters=characters or [],
            locations=locations or [],
            props=props or [],
            wardrobe_notes=wardrobe_notes,
            sound_notes=sound_notes,
            camera_notes=camera_notes,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        bible_dir = docs_dir(Path(root or ".").resolve() / ".brandly" / project_id, "bible")
        bible_dir.mkdir(parents=True, exist_ok=True)
        path = bible_dir / "production_bible.json"
        write_json(path, bible.model_dump())
        return {
            "project_id": project_id,
            "path": str(path),
            "title": title,
            "logline": logline,
            "characters": len(bible.characters),
            "locations": len(bible.locations),
        }
    except Exception as e:
        return {"error": f"write_bible: {e}"}


def _read_bible(
    project_id: str,
    root: str | None = None,
) -> dict[str, Any]:
    """Read the production bible from ``.brandly/{id}/docs/bible/``."""
    try:
        from brandly_cli.io import read_json

        path = docs_dir(Path(root or ".").resolve() / ".brandly" / project_id, "bible") / "production_bible.json"
        if not path.exists():
            return {"error": f"bible not found for project {project_id}"}
        data = read_json(path)
        return {"project_id": project_id, "bible": data}
    except Exception as e:
        return {"error": f"read_bible: {e}"}


# ---------------------------------------------------------------------------
# Tool: write_screenplay / read_screenplay
# ---------------------------------------------------------------------------

def _write_screenplay(
    project_id: str,
    title: str,
    logline: str,
    acts: list[dict[str, Any]] | None = None,
    scenes: list[dict[str, Any]] | None = None,
    total_duration: int = 0,
    tone: str = "",
    pacing: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Write the screenplay/beat sheet to ``.brandly/{id}/docs/screenplay/``."""
    try:
        screenplay = ScreenplayContent(
            project_id=project_id,
            title=title,
            logline=logline,
            acts=acts or [],
            scenes=scenes or [],
            total_duration=total_duration,
            tone=tone,
            pacing=pacing,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        screenplay_dir = docs_dir(Path(root or ".").resolve() / ".brandly" / project_id, "screenplay")
        screenplay_dir.mkdir(parents=True, exist_ok=True)
        path = screenplay_dir / "screenplay.json"
        write_json(path, screenplay.model_dump())
        return {
            "project_id": project_id,
            "path": str(path),
            "title": title,
            "scenes": len(screenplay.scenes),
            "total_duration": total_duration,
        }
    except Exception as e:
        return {"error": f"write_screenplay: {e}"}


def _read_screenplay(
    project_id: str,
    root: str | None = None,
) -> dict[str, Any]:
    """Read the screenplay from ``.brandly/{id}/docs/screenplay/``."""
    try:
        from brandly_cli.io import read_json

        path = docs_dir(Path(root or ".").resolve() / ".brandly" / project_id, "screenplay") / "screenplay.json"
        if not path.exists():
            return {"error": f"screenplay not found for project {project_id}"}
        data = read_json(path)
        return {"project_id": project_id, "screenplay": data}
    except Exception as e:
        return {"error": f"read_screenplay: {e}"}


# ---------------------------------------------------------------------------
# Tool registry — documents domain
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "write_bible": {
        "handler": _write_bible,
        "schema": {
            "type": "object",
            "title": "Write Bible",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "title": {"type": "string", "description": "Production title."},
                "logline": {"type": "string", "description": "One-sentence logline."},
                "tone": {"type": "string", "description": "Tone of the piece."},
                "genre": {"type": "string", "description": "Genre."},
                "visual_style": {
                    "type": "string",
                    "default": "cinematic",
                    "description": "Visual style (cinematic, short-film, ugc, ...).",
                },
                "color_palette": {"type": "string", "description": "Color palette notes."},
                "characters": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Character definitions from the bible.",
                },
                "locations": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Location definitions from the bible.",
                },
                "props": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Prop definitions from the bible.",
                },
                "wardrobe_notes": {"type": "string", "description": "Wardrobe notes."},
                "sound_notes": {"type": "string", "description": "Sound design notes."},
                "camera_notes": {"type": "string", "description": "Camera notes."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "title", "logline"],
        },
        "description": (
            "Write the production bible to .brandly/{id}/docs/bible/. The bible "
            "is the single source of truth that informs cast, wardrobe, "
            "location, sound, director, DoP, and cascade tools downstream."
        ),
    },
    "read_bible": {
        "handler": _read_bible,
        "schema": {
            "type": "object",
            "title": "Read Bible",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "root": {"type": "string"},
            },
            "required": ["project_id"],
        },
        "description": "Read the production bible from .brandly/{id}/docs/bible/.",
    },
    "write_screenplay": {
        "handler": _write_screenplay,
        "schema": {
            "type": "object",
            "title": "Write Screenplay",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "title": {"type": "string", "description": "Screenplay title."},
                "logline": {"type": "string", "description": "One-sentence logline."},
                "acts": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Act structures.",
                },
                "scenes": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Scenes with description, duration, visual_notes, prompt.",
                },
                "total_duration": {
                    "type": "integer",
                    "default": 0,
                    "description": "Total duration in seconds.",
                },
                "tone": {"type": "string", "description": "Tone."},
                "pacing": {"type": "string", "description": "Pacing."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "title", "logline"],
        },
        "description": (
            "Write the screenplay/beat sheet to .brandly/{id}/docs/screenplay/. "
            "Written first so every downstream tool anchors to the script."
        ),
    },
    "read_screenplay": {
        "handler": _read_screenplay,
        "schema": {
            "type": "object",
            "title": "Read Screenplay",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "root": {"type": "string"},
            },
            "required": ["project_id"],
        },
        "description": "Read the screenplay from .brandly/{id}/docs/screenplay/.",
    },
}
