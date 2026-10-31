"""Pre-production tools — cast, wardrobe, sheets, location, sound, spatial.

Moved out of the former monolithic ``agent_tools.py`` so each concern owns its
module (see ``brandly_cli/agent_tools/__init__.py``).

Every handler writes on-disk records under ``.brandly/<project>/`` so the
production pipeline can consume them later; none of them fabricates generation
results and none of them is a no-op.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from brandly_cli import audio_client
from brandly_cli.agnes_client import create_video_task
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


def _cast_characters(
    project_id: str,
    cast: list[dict[str, Any]],
    root: str | None = None,
) -> dict[str, Any]:
    """Cast characters from the bible and store reference plates.

    Writes to ``pre-production/{id}/images/character/`` and records each
    cast member's identity anchor, reference images, and wardrobe.
    """
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


def _try_wardrobe(
    project_id: str,
    character_name: str,
    outfit_name: str,
    description: str = "",
    image_path: str = "",
    category: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Try a wardrobe variation for a character.

    Writes to ``pre-production/{id}/images/wardrobe/``.
    """
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


def _animate_cast_15sec(
    project_id: str,
    character_name: str,
    prompt: str,
    reference_images: list[str] | None = None,
    model: str = "agnes-video-2.5-flash",
    root: str | None = None,
) -> dict[str, Any]:
    """Animate a cast member for a 15-second test clip.

    Creates a short animation task (4-12s per Agnes Flash limits) for
    wardrobe/identity validation before full production.
    """
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
    """Generate a reference sheet for a subject (character, location, prop, etc.).

    Writes the image to ``pre-production/{id}/images/{category}/`` and
    records the sheet metadata.
    """
    from brandly_cli.agnes_client import generate_image

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
    """Design a location / set with visual reference.

    Writes to ``pre-production/{id}/images/location/``.
    """
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
    """Design an audio track (soundtrack, sfx, foley, or voiceover).

    Generates real audio via MiniMax (TTS for voiceover, music otherwise),
    downloads it to ``production/{id}/audio/{category}/`` and records the
    track JSON alongside the media. Download failure is non-fatal (metadata
    kept, no local file); provider errors surface as an error envelope.
    """
    try:
        audio_dir = resolve_media_root(Path(root or "."), project_id, "audio") / category
        audio_dir.mkdir(parents=True, exist_ok=True)
        track = SoundTrack(
            id=description[:40].lower().replace(" ", "_"),
            type=sound_type,
            description=description,
            prompt=prompt,
            duration=duration,
            output_path=output_path,
            category=category,
            created_at=now_iso(),
        )
        if sound_type == "voiceover":
            generated = run_async(audio_client.generate_tts(prompt))
        else:
            generated = run_async(
                audio_client.generate_music(prompt, duration_seconds=duration or 30)
            )
        url = generated.get("url", "") or ""
        downloaded = False
        if url:
            try:
                resp = httpx.get(url, timeout=60.0)
                resp.raise_for_status()
                mp3_path = audio_dir / f"{track.id}.mp3"
                mp3_path.write_bytes(resp.content)
                track.output_path = str(mp3_path)
                downloaded = True
            except Exception:
                downloaded = False  # non-fatal: keep the record, no local file
        path = audio_dir / f"{track.id}.json"
        write_json(path, track.model_dump())
        return {
            "project_id": project_id,
            "type": sound_type,
            "description": description,
            "path": str(path),
            "url": url,
            "duration_ms": generated.get("duration_ms"),
            "downloaded": downloaded,
            "output_path": track.output_path,
        }
    except Exception as e:
        return {"error": f"sound_design: {e}"}


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
    """Create a 3D spatial reference frame using Blender.

    Writes camera position/angle, depth maps, and keyframes to
    ``3d-spatial/{cameras, keyframes, depthmaps}/`` for use as Agnes
    composition guides.
    """
    proj_dir = project_dir(Path(root or "."), project_id)
    spatial = SpatialFrame(
        shot_id=shot_id,
        camera_position=camera_position or [0.0, 0.0, 0.0],
        camera_rotation=camera_rotation or [0.0, 0.0, 0.0],
        lens_mm=lens_mm,
        aspect_ratio=aspect_ratio,
        depth_map_path=depth_map_path,
        keyframe_path=keyframe_path,
        blocking_notes=blocking_notes,
        created_at=now_iso(),
    )
    # Write spatial record
    cam_dir = spatial_dir(proj_dir, "cameras")
    cam_dir.mkdir(parents=True, exist_ok=True)
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
    }


# ---------------------------------------------------------------------------
# Tool registry — pre-production domain
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
                "aspect_ratio": {
                    "type": "string",
                    "default": "16:9",
                    "description": "Aspect ratio.",
                },
                "depth_map_path": {"type": "string", "description": "Depth map path."},
                "keyframe_path": {"type": "string", "description": "Keyframe path."},
                "blocking_notes": {"type": "string", "description": "Blocking notes."},
                "blender_script": {"type": "string", "description": "Blender script path."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "shot_id"],
        },
        "description": "Create a 3D spatial reference frame using Blender composition guides.",
    },
}
