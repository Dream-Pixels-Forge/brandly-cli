"""Pre-production tools — cast, wardrobe, sheets, location, sound, spatial.

Tools map to skills by domain:

* ``cast_characters``, ``try_wardrobe`` → ``brandly-casting``
* ``animate_cast_15sec`` → ``brandly-video-generation``
* ``generate_sheet`` → subject-type dispatches to
  ``brandly-character-sheet`` / ``brandly-location-sheet`` /
  ``brandly-object-sheet`` / ``brandly-vehicle-sheet`` /
  ``brandly-mecha-sheet`` / ``brandly-animal-sheet`` / ``brandly-plant-sheet``
* ``location_architect`` → ``brandly-location-sheet``
* ``sound_design`` → no dedicated skill yet
* ``spatial_blocking`` → ``brandly-3d-spatial``
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from brandly_cli.agnes_client import create_video_task, generate_image
from brandly_cli.async_compat import run_async
from brandly_cli.io import now_iso, write_json
from brandly_cli.layout import project_dir, resolve_media_root, spatial_dir
from brandly_cli.types import (
    CastMember,
    LocationDesign,
    ReferenceSheet,
    SoundTrack,
    SpatialFrame,
    WardrobeTry,
)

# ---------------------------------------------------------------------------
# Tool: cast_characters
# ---------------------------------------------------------------------------

def _cast_characters(
    project_id: str,
    cast: list[dict[str, Any]],
    root: str | None = None,
) -> dict[str, Any]:
    """Cast characters from the bible and store reference plates."""
    try:
        cast_dir = resolve_media_root(Path(root or "."), project_id, "images") / "character"
        cast_dir.mkdir(parents=True, exist_ok=True)
        members: list[dict[str, Any]] = []
        for c in cast:
            member = CastMember(
                name=c.get("name", ""),
                role=c.get("role", "supporting"),
                description=c.get("description", ""),
                reference_images=c.get("reference_images", []),
                wardrobe=c.get("wardrobe", []),
                voice_notes=c.get("voice_notes", ""),
                created_at=now_iso(),
            )
            members.append(member.model_dump())
        path = cast_dir / "cast.json"
        write_json(path, {"project_id": project_id, "cast": members, "updated_at": now_iso()})
        return {
            "project_id": project_id,
            "path": str(path),
            "cast_count": len(members),
            "directory": str(cast_dir),
        }
    except Exception as e:
        return {"error": f"cast_characters: {e}"}


# ---------------------------------------------------------------------------
# Tool: try_wardrobe
# ---------------------------------------------------------------------------

def _try_wardrobe(
    project_id: str,
    character_name: str,
    outfit_name: str,
    description: str = "",
    image_path: str = "",
    category: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Try a wardrobe variation for a character."""
    try:
        wardrobe_dir = resolve_media_root(Path(root or "."), project_id, "images") / "wardrobe"
        wardrobe_dir.mkdir(parents=True, exist_ok=True)
        try_ = WardrobeTry(
            character_name=character_name,
            outfit_name=outfit_name,
            description=description,
            image_path=image_path,
            category=category,
            created_at=now_iso(),
        )
        path = wardrobe_dir / f"{character_name}_{outfit_name}.json"
        write_json(path, try_.model_dump())
        return {
            "project_id": project_id,
            "character": character_name,
            "outfit": outfit_name,
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"try_wardrobe: {e}"}


# ---------------------------------------------------------------------------
# Tool: animate_cast_15sec
# ---------------------------------------------------------------------------

def _animate_cast_15sec(
    project_id: str,
    character_name: str,
    prompt: str,
    reference_images: list[str] | None = None,
    model: str = "agnes-video-2.5-flash",
    root: str | None = None,
) -> dict[str, Any]:
    """Animate a cast member for a short test clip (wardrobe/identity validation)."""
    try:
        result = run_async(
            create_video_task(
                prompt,
                model=model,
                mode="reference" if reference_images else "text",
                duration=5,
                aspect_ratio="16:9",
                size="720P",
                reference_images=reference_images,
            )
        )
        return {
            "project_id": project_id,
            "character": character_name,
            "video_id": result.get("video_id"),
            "status": result.get("status"),
            "mode": result.get("mode"),
        }
    except Exception as e:
        return {"error": f"animate_cast_15sec: {e}"}


# ---------------------------------------------------------------------------
# Tool: generate_sheet
# ---------------------------------------------------------------------------

def _generate_sheet(
    project_id: str,
    subject_type: str,
    subject_name: str,
    prompt: str,
    category: str = "",
    model: str = "agnes-image-2.5-flash",
    size: str = "2K",
    ratio: str = "16:9",
    root: str | None = None,
) -> dict[str, Any]:
    """Generate a reference sheet for a subject under pre-production/{id}/images/{category}/."""
    try:
        result = run_async(
            generate_image(prompt, model=model, size=size, ratio=ratio)
        )
        sheet_dir = resolve_media_root(Path(root or "."), project_id, "images") / (
            category or subject_type
        )
        sheet_dir.mkdir(parents=True, exist_ok=True)
        sheet = ReferenceSheet(
            subject_type=subject_type,
            subject_name=subject_name,
            image_path=result.get("url", ""),
            category=category or subject_type,
            prompt=prompt,
            created_at=now_iso(),
        )
        path = sheet_dir / f"{subject_type}_{subject_name}.json"
        write_json(path, sheet.model_dump())
        return {
            "project_id": project_id,
            "subject_type": subject_type,
            "subject_name": subject_name,
            "image_url": result.get("url"),
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"generate_sheet: {e}"}


# ---------------------------------------------------------------------------
# Tool: location_architect
# ---------------------------------------------------------------------------

def _location_architect(
    project_id: str,
    name: str,
    description: str = "",
    prompt: str = "",
    image_path: str = "",
    category: str = "exterior",
    lighting_notes: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Design a location / set with visual reference."""
    try:
        loc_dir = resolve_media_root(Path(root or "."), project_id, "images") / "location"
        loc_dir.mkdir(parents=True, exist_ok=True)
        location = LocationDesign(
            name=name,
            description=description,
            image_path=image_path,
            category=category,
            lighting_notes=lighting_notes,
            created_at=now_iso(),
        )
        path = loc_dir / f"{name}.json"
        write_json(path, location.model_dump())
        return {
            "project_id": project_id,
            "location": name,
            "category": category,
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"location_architect: {e}"}


# ---------------------------------------------------------------------------
# Tool: sound_design
# ---------------------------------------------------------------------------

def _sound_design(
    project_id: str,
    sound_type: str,
    description: str,
    prompt: str,
    duration: int | None = None,
    output_path: str = "",
    category: str = "general",
    root: str | None = None,
) -> dict[str, Any]:
    """Design an audio track (soundtrack, sfx, foley, voiceover).

    Generates the audio via MiniMax (TTS for voiceover, music generation for
    music/sfx/foley), downloads the result to
    ``production/<id>/audio/<category>/<track_id>.mp3``, and records the
    metadata.
    """
    try:
        from brandly_cli.audio_client import generate_music, generate_tts

        audio_dir = resolve_media_root(Path(root or "."), project_id, "audio") / category
        audio_dir.mkdir(parents=True, exist_ok=True)
        track_id = description[:40].lower().replace(" ", "_")
        local_path = str(audio_dir / f"{track_id}.mp3")

        is_voiceover = sound_type == "voiceover"

        if is_voiceover:
            result = run_async(
                generate_tts(
                    text=prompt,
                    model="speech-2.8-hd",
                    voice_id="English_Insightful_Speaker",
                    output_format="url",
                )
            )
        else:
            result = run_async(
                generate_music(
                    prompt=prompt,
                    model="music-3.0",
                    duration_seconds=duration or 30,
                    instrumental=(sound_type != "voiceover"),
                )
            )

        remote_url = result.get("url") or result.get("b64_json")
        duration_ms = result.get("duration_ms")

        # Download the audio file locally.
        downloaded = False
        if remote_url:
            try:
                resp = httpx.get(remote_url, timeout=60)
                resp.raise_for_status()
                Path(local_path).write_bytes(resp.content)
                downloaded = True
            except Exception:  # download failure is not fatal; metadata still recorded
                downloaded = False

        track = SoundTrack(
            id=track_id,
            type=sound_type,
            description=description,
            prompt=prompt,
            duration=duration,
            output_path=local_path if downloaded else "",
            category=category,
            created_at=now_iso(),
        )
        path = audio_dir / f"{track.id}.json"
        write_json(path, track.model_dump())
        return {
            "project_id": project_id,
            "type": sound_type,
            "description": description,
            "output_path": local_path if downloaded else "",
            "url": remote_url,
            "duration_ms": duration_ms,
            "path": str(path),
            "downloaded": downloaded,
        }
    except Exception as e:
        return {"error": f"sound_design: {e}"}


# ---------------------------------------------------------------------------
# Tool: spatial_blocking
# ---------------------------------------------------------------------------

def _spatial_blocking(
    project_id: str,
    shot_id: str,
    camera_position: list[float] | None = None,
    camera_rotation: list[float] | None = None,
    lens_mm: str = "50mm",
    aspect_ratio: str = "16:9",
    depth_map_path: str = "",
    keyframe_path: str = "",
    blocking_notes: str = "",
    blender_script: str | None = None,
    root: str | None = None,
) -> dict[str, Any]:
    """Create a 3D spatial reference frame using Blender."""
    proj_dir = project_dir(Path(root or "."), project_id)
    cam_dir = spatial_dir(proj_dir, "cameras")
    cam_dir.mkdir(parents=True, exist_ok=True)

    blender_config = {
        "resolution": [1920, 1080],
        "fps": 24,
        "cameras": [
            {
                "name": shot_id,
                "position": list(camera_position or [0.0, 0.0, 0.0]),
                "rotation": list(camera_rotation or [0.0, 0.0, 0.0]),
                "look_at": [0.0, 0.0, 0.0],
                "lens_mm": lens_mm,
                "aspect_ratio": aspect_ratio,
            }
        ],
    }

    blender_path = shutil.which("blender")
    render_result = None

    if blender_path:
        config_path = cam_dir / f"{shot_id}_config.json"
        write_json(config_path, blender_config)

        skills_dir = Path(__file__).resolve().parent.parent / "skills" / "brandly-3d-spatial" / "scripts"
        blender_script_path = skills_dir / "playblast_renderer.py"

        if blender_script_path.exists():
            try:
                result = subprocess.run(
                    [
                        blender_path,
                        "--background",
                        "--python",
                        str(blender_script_path),
                        "--",
                        "--config",
                        str(config_path),
                        "--output",
                        str(cam_dir),
                        "--mode",
                        "single",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    render_summary_path = cam_dir / "render_summary.json"
                    if render_summary_path.exists():
                        render_result = json.loads(render_summary_path.read_text())
                else:
                    print(
                        f"[yellow]⚠ Blender render failed: {result.stderr[:200]}[/yellow]"
                    )
            except Exception as e:
                print(f"[yellow]⚠ Blender execution failed: {e}[/yellow]")
        else:
            print(
                "[yellow]⚠ Blender not found. Install Blender for 3D spatial rendering.[/yellow]"
            )

    spatial = SpatialFrame(
        shot_id=shot_id,
        camera_position=list(camera_position or [0.0, 0.0, 0.0]),
        camera_rotation=list(camera_rotation or [0.0, 0.0, 0.0]),
        lens_mm=lens_mm,
        aspect_ratio=aspect_ratio,
        depth_map_path=depth_map_path,
        keyframe_path=keyframe_path,
        blocking_notes=blocking_notes,
        created_at=now_iso(),
    )
    path = cam_dir / f"{shot_id}.json"
    write_json(path, spatial.model_dump())
    return {
        "project_id": project_id,
        "shot_id": shot_id,
        "camera_position": spatial.camera_position,
        "camera_rotation": spatial.camera_rotation,
        "lens_mm": lens_mm,
        "aspect_ratio": aspect_ratio,
        "path": str(path),
        "blender_script": blender_script,
        "blender_render_result": render_result,
    }# ---------------------------------------------------------------------------
# Tool registry — pre_production domain
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "cast_characters": {
        "handler": _cast_characters,
        "schema": {
            "type": "object",
            "title": "Cast Characters",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "cast": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "description": {"type": "string"},
                            "reference_images": {"type": "array", "items": {"type": "string"}},
                            "wardrobe": {"type": "array", "items": {"type": "string"}},
                            "voice_notes": {"type": "string"},
                        },
                        "required": ["name", "role"],
                    },
                    "description": "Cast members with identity anchors.",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "cast"],
        },
        "description": (
            "Cast characters from the bible and store reference plates under "
            "pre-production/{id}/images/character/."
        ),
    },
    "try_wardrobe": {
        "handler": _try_wardrobe,
        "schema": {
            "type": "object",
            "title": "Try Wardrobe",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "character_name": {"type": "string", "description": "Character name."},
                "outfit_name": {"type": "string", "description": "Outfit name."},
                "description": {"type": "string", "description": "Outfit description."},
                "image_path": {"type": "string", "description": "Wardrobe image path."},
                "category": {"type": "string", "description": "Wardrobe category (casual, formal, period, ...)."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "character_name", "outfit_name"],
        },
        "description": "Try a wardrobe variation for a character under pre-production/{id}/images/wardrobe/.",
    },
    "animate_cast_15sec": {
        "handler": _animate_cast_15sec,
        "schema": {
            "type": "object",
            "title": "Animate Cast 15sec",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "character_name": {"type": "string", "description": "Character name."},
                "prompt": {"type": "string", "description": "Animation prompt."},
                "reference_images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reference images for identity consistency.",
                },
                "model": {
                    "type": "string",
                    "default": "agnes-video-2.5-flash",
                    "description": "Video model.",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "character_name", "prompt"],
        },
        "description": "Animate a cast member for a short test clip (wardrobe/identity validation).",
    },
    "generate_sheet": {
        "handler": _generate_sheet,
        "schema": {
            "type": "object",
            "title": "Generate Sheet",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "subject_type": {
                    "type": "string",
                    "enum": ["character", "location", "prop", "vehicle", "mecha", "animal", "plant"],
                    "description": "Subject type.",
                },
                "subject_name": {"type": "string", "description": "Subject name."},
                "prompt": {"type": "string", "description": "Image generation prompt."},
                "category": {"type": "string", "description": "Image category folder (defaults to subject_type)."},
                "model": {
                    "type": "string",
                    "default": "agnes-image-2.5-flash",
                    "description": "Image model.",
                },
                "size": {
                    "type": "string",
                    "default": "2K",
                    "description": "Image size tier (1K/2K/3K/4K).",
                },
                "ratio": {
                    "type": "string",
                    "default": "16:9",
                    "description": "Aspect ratio.",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "subject_type", "subject_name", "prompt"],
        },
        "description": "Generate a reference sheet for a subject under pre-production/{id}/images/{category}/.",
    },
    "location_architect": {
        "handler": _location_architect,
        "schema": {
            "type": "object",
            "title": "Location Architect",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "name": {"type": "string", "description": "Location name."},
                "description": {"type": "string", "description": "Location description."},
                "prompt": {"type": "string", "description": "Image generation prompt for the location."},
                "image_path": {"type": "string", "description": "Existing reference image path (optional)."},
                "category": {
                    "type": "string",
                    "default": "exterior",
                    "description": "Location category (interior, exterior, studio, practical).",
                },
                "lighting_notes": {"type": "string", "description": "Lighting notes for the location."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "name"],
        },
        "description": "Design a location/set with visual reference under pre-production/{id}/images/location/.",
    },
    "sound_design": {
        "handler": _sound_design,
        "schema": {
            "type": "object",
            "title": "Sound Design",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "sound_type": {
                    "type": "string",
                    "enum": ["music", "sfx", "foley", "voiceover"],
                    "description": "Audio type.",
                },
                "description": {"type": "string", "description": "Track description."},
                "prompt": {"type": "string", "description": "Audio generation prompt."},
                "duration": {"type": "integer", "description": "Duration in seconds."},
                "output_path": {"type": "string", "description": "Output path."},
                "category": {
                    "type": "string",
                    "default": "general",
                    "description": "Audio category (soundtrack, sfx, foley, voiceover, general).",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "sound_type", "description", "prompt"],
        },
        "description": "Design an audio track (soundtrack, sfx, foley, voiceover) under production/{id}/audio/{category}/.",
    },
    "spatial_blocking": {
        "handler": _spatial_blocking,
        "schema": {
            "type": "object",
            "title": "Spatial Blocking",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "shot_id": {"type": "string", "description": "Shot id."},
                "camera_position": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Camera position [x, y, z].",
                },
                "camera_rotation": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Camera rotation [x, y, z].",
                },
                "lens_mm": {"type": "string", "default": "50mm", "description": "Lens focal length."},
                "aspect_ratio": {"type": "string", "default": "16:9", "description": "Aspect ratio."},
                "depth_map_path": {"type": "string", "description": "Depth map render path."},
                "keyframe_path": {"type": "string", "description": "Keyframe render path."},
                "blocking_notes": {"type": "string", "description": "Blocking notes."},
                "blender_script": {"type": "string", "description": "Blender script used to generate the frame."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "shot_id"],
        },
        "description": (
            "Create a 3D spatial reference frame using Blender. Writes camera "
            "position/angle, depth maps, and keyframes to 3d-spatial/ for use "
            "as Agnes composition guides."
        ),
    },
}
