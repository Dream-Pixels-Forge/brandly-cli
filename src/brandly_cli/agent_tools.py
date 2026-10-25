"""Built-in tool handlers for the Agnes AI agent loop.

Each tool is a Python callable that takes only JSON-serializable arguments
and returns a JSON-serializable result. The tool *descriptor* (name + JSON
schema) is exposed to the Agnes model via the OpenAI-compatible
``tools`` field, and this module provides the handler that actually
executes it on the client side.

Tools are intentionally small and read-only: they mirror the state the
brandly CLI already exposes (project data, Agnes jobs, model catalog)
so an agent can answer questions like "which projects have failed
videos?" without any new user input.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Tool handler type
#
# A handler is a function (sync or async) that takes keyword arguments and
# returns a JSON-serializable value.  ``agent_tool_loop`` will await the
# result if it's a coroutine, and stringify non-strings with ``json.dumps``.
# ---------------------------------------------------------------------------

ToolHandler = Callable[..., Any] | Callable[..., Awaitable[Any]]


# ---------------------------------------------------------------------------
# Tool: list_projects
# ---------------------------------------------------------------------------

def _list_projects(
    status: str | None = None,
    limit: int = 20,
    root: str | None = None,
) -> dict[str, Any]:
    """List brandly projects on disk, optionally filtered by status."""
    from brandly_cli.async_compat import run_async

    try:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(Path(root or "."))
        projects = run_async(pm.list_with_status())
        if status:
            projects = [p for p in projects if p.get("status") == status]
        projects = projects[:limit]
        return {
            "count": len(projects),
            "projects": [
                {
                    "id": p.get("id", ""),
                    "name": p.get("name", ""),
                    "status": p.get("status", ""),
                    "updated_at": p.get("updated_at", ""),
                }
                for p in projects
            ],
        }
    except Exception as e:  # pragma: no cover - safety net
        return {"error": f"list_projects: {e}"}


# ---------------------------------------------------------------------------
# Tool: get_project
# ---------------------------------------------------------------------------

def _get_project(project_id: str, root: str | None = None) -> dict[str, Any]:
    """Fetch a single project by ID from the project manager."""
    from brandly_cli.async_compat import run_async

    try:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(Path(root or "."))
        data = run_async(pm.read(project_id))
        if not data:
            return {"error": f"project {project_id} not found"}
        model_dump = getattr(data, "model_dump", None)
        return model_dump() if callable(model_dump) else {"id": project_id}
    except Exception as e:
        return {"error": f"get_project: {e}"}


# ---------------------------------------------------------------------------
# Tool: list_jobs (Agnes video jobs)
# ---------------------------------------------------------------------------

def _list_jobs(
    status: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """List recent Agnes video-generation jobs (read-only)."""
    from brandly_cli.async_compat import run_async

    try:
        from brandly_cli.agnes_client import list_jobs

        return {"jobs": run_async(list_jobs(status=status, limit=limit))}
    except Exception as e:
        return {"error": f"list_jobs: {e}"}


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
    from brandly_cli.async_compat import run_async

    try:
        from brandly_cli.agnes_client import generate_image

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
# Studio tools (issue #60): same handlers the web routes use, exposed to the
# agent loop so the studio UI actions need no ad-hoc tools.
# ---------------------------------------------------------------------------

def _get_timeline(project_id: str, root: str | None = None) -> dict[str, Any]:
    """Return the timeline (clips, fps, aspect ratio) for a project."""
    try:
        from brandly_cli.web.state import TimelineState

        state = TimelineState(project_id, Path(root or ".").resolve())
        timeline = state.load()
        return {
            "project_id": project_id,
            "clips": [c.model_dump() for c in timeline.clips],
            "fps": timeline.fps,
            "aspect_ratio": timeline.aspect_ratio,
            "color_grade": timeline.color_grade,
        }
    except Exception as e:
        return {"error": f"get_timeline: {e}"}


def _update_clip(
    project_id: str,
    clip_id: str,
    updates: dict[str, Any],
    root: str | None = None,
) -> dict[str, Any]:
    """Patch clip fields (prompt, duration, volume, transition, style)."""
    try:
        from brandly_cli.web.models import ClipUpdate
        from brandly_cli.web.state import TimelineState

        state = TimelineState(project_id, Path(root or ".").resolve())
        if state.get_clip(clip_id) is None:
            return {"error": f"clip not found: {clip_id}"}
        updated = state.update_clip(clip_id, ClipUpdate(**updates))
        if updated is None:
            return {"error": f"update_clip failed: {clip_id}"}
        return {"clip_id": clip_id, "clip": updated.model_dump()}
    except Exception as e:
        return {"error": f"update_clip: {e}"}


def _reorder_timeline(
    project_id: str,
    order: list[str],
    root: str | None = None,
) -> dict[str, Any]:
    """Reorder timeline clips (mirrors PUT /api/projects/{id}/timeline)."""
    try:
        from brandly_cli.web.models import Clip as ClipModel
        from brandly_cli.web.state import TimelineState

        state = TimelineState(project_id, Path(root or ".").resolve())
        timeline = state.load()
        by_id = {c.id: c for c in timeline.clips}
        unknown = [cid for cid in order if cid not in by_id]
        if unknown:
            return {"error": f"unknown clip ids: {unknown}"}
        ordered = [by_id[cid] for cid in order]
        remaining = [c for c in timeline.clips if c.id not in set(order)]
        reordered = ordered + remaining
        state.replace_clips([ClipModel(**c.model_dump()) for c in reordered])
        return {"project_id": project_id, "order": [c.id for c in reordered]}
    except Exception as e:
        return {"error": f"reorder_timeline: {e}"}


def _run_gate(
    project_id: str,
    clip_id: str,
    root: str | None = None,
) -> dict[str, Any]:
    """Run the deterministic quality gate on a clip (no AI, offline)."""
    from brandly_cli.async_compat import run_async

    try:
        from brandly_cli.quality_gate import verify_element
        from brandly_cli.web import deps

        root_path = Path(root or ".").resolve()
        _, media = deps.require_clip_media(root_path, project_id, clip_id)
        result = run_async(
            verify_element(
                media,
                use_ai=False,
                root=root_path,
                project_id=project_id,
                write_report=False,
            )
        )
        return {"clip_id": clip_id, "status": result.status, "score": result.score}
    except Exception as e:
        return {"error": f"run_gate: {e}"}


# ---------------------------------------------------------------------------
# .brandly Documents — Bible & Screenplay (foundation layer)
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
    """Write the production bible to ``.brandly/{id}/docs/bible/``.

    The bible is the single source of truth that informs cast, wardrobe,
    location, sound, director, DoP, and cascade tools downstream.
    """
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import docs_dir
    from brandly_cli.types import BibleContent

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
    from brandly_cli.io import read_json
    from brandly_cli.layout import docs_dir

    try:
        path = docs_dir(Path(root or ".").resolve() / ".brandly" / project_id, "bible") / "production_bible.json"
        if not path.exists():
            return {"error": f"bible not found for project {project_id}"}
        data = read_json(path)
        return {"project_id": project_id, "bible": data}
    except Exception as e:
        return {"error": f"read_bible: {e}"}


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
    """Write the screenplay/beat sheet to ``.brandly/{id}/docs/screenplay/``.

    Written first (before cast/wardrobe/location/sound) so every downstream
    tool can anchor to the script.
    """
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import docs_dir
    from brandly_cli.types import ScreenplayContent

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
    from brandly_cli.io import read_json
    from brandly_cli.layout import docs_dir

    try:
        path = docs_dir(Path(root or ".").resolve() / ".brandly" / project_id, "screenplay") / "screenplay.json"
        if not path.exists():
            return {"error": f"screenplay not found for project {project_id}"}
        data = read_json(path)
        return {"project_id": project_id, "screenplay": data}
    except Exception as e:
        return {"error": f"read_screenplay: {e}"}


# ---------------------------------------------------------------------------
# Pre-production — Cast, Wardrobe, Sheets, Location, Sound, Spatial
# ---------------------------------------------------------------------------


def _cast_characters(
    project_id: str,
    cast: list[dict[str, Any]],
    root: str | None = None,
) -> dict[str, Any]:
    """Cast characters from the bible and store reference plates.

    Writes to ``pre-production/{id}/images/character/`` and records each
    cast member's identity anchor, reference images, and wardrobe.
    """
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import resolve_media_root
    from brandly_cli.types import CastMember

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
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import resolve_media_root
    from brandly_cli.types import WardrobeTry

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
    from brandly_cli.agnes_client import create_video_task
    from brandly_cli.async_compat import run_async

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
    from brandly_cli.async_compat import run_async
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import resolve_media_root
    from brandly_cli.types import ReferenceSheet

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
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import resolve_media_root
    from brandly_cli.types import LocationDesign

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

    Writes to ``production/{id}/audio/{category}/``.
    """
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import resolve_media_root
    from brandly_cli.types import SoundTrack

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
        path = audio_dir / f"{track.id}.json"
        write_json(path, track.model_dump())
        return {
            "project_id": project_id,
            "type": sound_type,
            "description": description,
            "path": str(path),
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
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import project_dir, spatial_dir
    from brandly_cli.types import SpatialFrame

    try:
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
    except Exception as e:
        return {"error": f"spatial_blocking: {e}"}


# ---------------------------------------------------------------------------
# Production — Director, DoP, Cascade, Editor
# ---------------------------------------------------------------------------


def _director(
    project_id: str,
    shot_id: str,
    scene_id: str,
    prompt: str,
    model: str = "agnes-video-2.5-flash",
    style: str = "cinematic",
    duration: int = 5,
    aspect_ratio: str = "16:9",
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    reference_roles: list[str] | None = None,
    camera_notes: str = "",
    lighting_notes: str = "",
    sound_notes: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Director's shot-by-shot direction for a single shot.

    Creates a video generation task with full directorial control —
    camera, lighting, sound, references, and style annotations.
    """
    from brandly_cli.agnes_client import create_video_task
    from brandly_cli.async_compat import run_async
    from brandly_cli.io import now_iso
    from brandly_cli.types import ShotDirection

    try:
        direction = ShotDirection(
            shot_id=shot_id,
            scene_id=scene_id,
            prompt=prompt,
            model=model,
            style=style,
            duration=duration,
            aspect_ratio=aspect_ratio,
            first_frame=first_frame,
            last_frame=last_frame,
            reference_images=reference_images or [],
            reference_roles=reference_roles or [],
            camera_notes=camera_notes,
            lighting_notes=lighting_notes,
            sound_notes=sound_notes,
            created_at=now_iso(),
        )
        result = run_async(
            create_video_task(
                prompt,
                model=model,
                mode="reference" if reference_images else "text",
                duration=duration,
                aspect_ratio=aspect_ratio,
                size="720P",
                first_frame=first_frame,
                last_frame=last_frame,
                reference_images=reference_images,
            )
        )
        return {
            "project_id": project_id,
            "shot_id": shot_id,
            "scene_id": scene_id,
            "video_id": result.get("video_id"),
            "status": result.get("status"),
            "mode": result.get("mode"),
            "direction": direction.model_dump(),
        }
    except Exception as e:
        return {"error": f"director: {e}"}


def _cascade(
    project_id: str,
    stages: list[dict[str, Any]],
    root: str | None = None,
) -> dict[str, Any]:
    """Run a cinematic high-end cascade pipeline.

    Executes stages sequentially through the phase chain
    (trends → concept → bible → casting → screenplay → script → asset
    → audio → re_edit → validate → publish), with per-stage gates.
    Each stage maps to a real brandly tool.
    """
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import project_dir
    from brandly_cli.types import CascadeStage

    try:
        proj_dir = project_dir(Path(root or "."), project_id)
        general_dir = proj_dir / "docs" / "general"
        general_dir.mkdir(parents=True, exist_ok=True)

        cascade_stages: list[dict[str, Any]] = []
        for s in stages:
            stage = CascadeStage(
                name=s.get("name", ""),
                phase=s.get("phase", "init"),
                tool=s.get("tool", ""),
                input=s.get("input", {}),
                output={},
                status="pending",
                gate_passed=None,
                created_at=now_iso(),
            )
            cascade_stages.append(stage.model_dump())

        path = general_dir / f"cascade_{project_id}.json"
        write_json(path, {
            "project_id": project_id,
            "stages": cascade_stages,
            "updated_at": now_iso(),
        })
        return {
            "project_id": project_id,
            "stage_count": len(cascade_stages),
            "path": str(path),
            "phases": [s.get("phase", "") for s in stages],
        }
    except Exception as e:
        return {"error": f"cascade: {e}"}


def _director_of_photography(
    project_id: str,
    shot_id: str,
    lens: str = "50mm",
    aperture: str = "f/2.8",
    lighting_setup: str = "three_point",
    color_grade: str = "cinematic",
    composition: str = "rule_of_thirds",
    camera_move: str = "static",
    notes: str = "",
    root: str | None = None,
) -> dict[str, Any]:
    """Director of Photography specifications for a shot or scene.

    Defines lens, aperture, lighting, color grade, composition, and
    camera movement — fed to the director tool as camera_notes.
    """
    from brandly_cli.io import write_json
    from brandly_cli.layout import project_dir
    from brandly_cli.types import DirectorOfPhotography

    try:
        proj_dir = project_dir(Path(root or "."), project_id)
        dop_dir = proj_dir / "docs" / "general"
        dop_dir.mkdir(parents=True, exist_ok=True)

        dop = DirectorOfPhotography(
            shot_id=shot_id,
            lens=lens,
            aperture=aperture,
            lighting_setup=lighting_setup,
            color_grade=color_grade,
            composition=composition,
            camera_move=camera_move,
            notes=notes,
        )
        path = dop_dir / f"dop_{shot_id}.json"
        write_json(path, dop.model_dump())
        return {
            "project_id": project_id,
            "shot_id": shot_id,
            "lens": lens,
            "lighting_setup": lighting_setup,
            "color_grade": color_grade,
            "composition": composition,
            "camera_move": camera_move,
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"director_of_photography: {e}"}


def _editor(
    project_id: str,
    clip_id: str,
    start_time: float = 0.0,
    end_time: float = 0.0,
    transition: str = "cut",
    transition_duration: float = 0.5,
    color_grade: str = "none",
    volume: float = 1.0,
    root: str | None = None,
) -> dict[str, Any]:
    """Editor's cut decision for a clip.

    Records edit decisions (trim, transition, grade, volume) for the
    stitch/assembly pipeline.
    """
    from brandly_cli.io import now_iso, write_json
    from brandly_cli.layout import project_dir
    from brandly_cli.types import EditDecision

    try:
        proj_dir = project_dir(Path(root or "."), project_id)
        edit_dir = proj_dir / "docs" / "tmp"
        edit_dir.mkdir(parents=True, exist_ok=True)

        decision = EditDecision(
            clip_id=clip_id,
            start_time=start_time,
            end_time=end_time,
            transition=transition,
            transition_duration=transition_duration,
            color_grade=color_grade,
            volume=volume,
            created_at=now_iso(),
        )
        path = edit_dir / f"edit_{clip_id}.json"
        write_json(path, decision.model_dump())
        return {
            "project_id": project_id,
            "clip_id": clip_id,
            "start_time": start_time,
            "end_time": end_time,
            "transition": transition,
            "color_grade": color_grade,
            "volume": volume,
            "path": str(path),
        }
    except Exception as e:
        return {"error": f"editor: {e}"}


# ---------------------------------------------------------------------------
# Tool registry (extended)
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "list_projects": {
        "handler": _list_projects,
        "schema": {
            "type": "object",
            "title": "List Projects",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "completed", "failed", "paused", "cancelled"],
                    "description": "Optional status filter.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                    "description": "Max projects to return.",
                },
                "root": {
                    "type": "string",
                    "description": "Project root directory (defaults to cwd).",
                },
            },
        },
        "description": "List brandly projects on disk, optionally filtered by status.",
    },
    "get_project": {
        "handler": _get_project,
        "schema": {
            "type": "object",
            "title": "Get Project",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID or slug of the project to fetch.",
                },
                "root": {
                    "type": "string",
                    "description": "Project root directory.",
                },
            },
            "required": ["project_id"],
        },
        "description": "Fetch a single project by ID, including phases and cost tracking.",
    },
    "list_jobs": {
        "handler": _list_jobs,
        "schema": {
            "type": "object",
            "title": "List Jobs",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "completed", "failed", "paused", "cancelled"],
                    "description": "Optional status filter.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                    "description": "Max jobs to return.",
                },
            },
        },
        "description": "List recent Agnes video-generation jobs (read-only).",
    },
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
                    "description": "Aspect ratio.",
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
    "get_timeline": {
        "handler": _get_timeline,
        "schema": {
            "type": "object",
            "title": "Get Timeline",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID or slug of the project.",
                },
                "root": {"type": "string", "description": "Project root directory."},
            },
            "required": ["project_id"],
        },
        "description": "Get a project's timeline: clips, fps, aspect ratio, color grade.",
    },
    "update_clip": {
        "handler": _update_clip,
        "schema": {
            "type": "object",
            "title": "Update Clip",
            "properties": {
                "project_id": {"type": "string"},
                "clip_id": {"type": "string"},
                "updates": {
                    "type": "object",
                    "description": "Clip fields to patch (prompt, duration, volume, transition_in, style).",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "clip_id", "updates"],
        },
        "description": "Update a single timeline clip (mirrors PATCH clip route).",
    },
    "reorder_timeline": {
        "handler": _reorder_timeline,
        "schema": {
            "type": "object",
            "title": "Reorder Timeline",
            "properties": {
                "project_id": {"type": "string"},
                "order": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Clip IDs in the desired order.",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "order"],
        },
        "description": "Reorder timeline clips (mirrors PUT timeline route).",
    },
    "run_gate": {
        "handler": _run_gate,
        "schema": {
            "type": "object",
            "title": "Run Gate",
            "properties": {
                "project_id": {"type": "string"},
                "clip_id": {"type": "string"},
                "root": {"type": "string"},
            },
            "required": ["project_id", "clip_id"],
        },
        "description": "Run the deterministic quality gate on a clip (offline, no AI).",
    },
    # --- .brandly Documents — Bible & Screenplay (foundation layer) ---
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
    # --- Pre-production — Cast, Wardrobe, Sheets, Location, Sound, Spatial ---
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
    # --- Production — Director, DoP, Cascade, Editor ---
    "director": {
        "handler": _director,
        "schema": {
            "type": "object",
            "title": "Director",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "shot_id": {"type": "string", "description": "Shot id."},
                "scene_id": {"type": "string", "description": "Scene id."},
                "prompt": {"type": "string", "description": "Shot direction prompt."},
                "model": {
                    "type": "string",
                    "default": "agnes-video-2.5-flash",
                    "description": "Video model.",
                },
                "style": {
                    "type": "string",
                    "default": "cinematic",
                    "description": "Video style (cinematic, short-film, ugc, ...).",
                },
                "duration": {"type": "integer", "default": 5, "description": "Shot duration in seconds."},
                "aspect_ratio": {"type": "string", "default": "16:9", "description": "Aspect ratio."},
                "first_frame": {"type": "string", "description": "First frame image path (keyframe mode)."},
                "last_frame": {"type": "string", "description": "Last frame image path (keyframe mode)."},
                "reference_images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reference images for consistency.",
                },
                "reference_roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reference image roles (character, environment, prop, ...).",
                },
                "camera_notes": {"type": "string", "description": "DoP camera notes."},
                "lighting_notes": {"type": "string", "description": "Lighting notes."},
                "sound_notes": {"type": "string", "description": "Sound notes."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "shot_id", "scene_id", "prompt"],
        },
        "description": "Director's shot-by-shot direction — creates a video task with full directorial control.",
    },
    "cascade": {
        "handler": _cascade,
        "schema": {
            "type": "object",
            "title": "Cascade",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "stages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phase": {"type": "string"},
                            "tool": {"type": "string"},
                            "input": {"type": "object"},
                        },
                        "required": ["name", "phase", "tool"],
                    },
                    "description": "Cascade stages mapped to brandly tools and phases.",
                },
                "root": {"type": "string"},
            },
            "required": ["project_id", "stages"],
        },
        "description": (
            "Run a cinematic high-end cascade pipeline through the phase chain "
            "(trends → concept → bible → casting → screenplay → script → asset "
            "→ audio → re_edit → validate → publish) with per-stage gates."
        ),
    },
    "director_of_photography": {
        "handler": _director_of_photography,
        "schema": {
            "type": "object",
            "title": "Director of Photography",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "shot_id": {"type": "string", "description": "Shot id."},
                "lens": {"type": "string", "default": "50mm", "description": "Lens focal length."},
                "aperture": {"type": "string", "default": "f/2.8", "description": "Aperture."},
                "lighting_setup": {
                    "type": "string",
                    "default": "three_point",
                    "description": "Lighting setup (three_point, natural, dramatic, golden_hour).",
                },
                "color_grade": {"type": "string", "default": "cinematic", "description": "Color grade."},
                "composition": {
                    "type": "string",
                    "default": "rule_of_thirds",
                    "description": "Composition rule.",
                },
                "camera_move": {
                    "type": "string",
                    "default": "static",
                    "description": "Camera movement (static, pan, tilt, dolly, tracking, orbital).",
                },
                "notes": {"type": "string", "description": "Additional DoP notes."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "shot_id"],
        },
        "description": "DoP specifications for a shot — lens, aperture, lighting, grade, composition, camera move.",
    },
    "editor": {
        "handler": _editor,
        "schema": {
            "type": "object",
            "title": "Editor",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "clip_id": {"type": "string", "description": "Clip id."},
                "start_time": {"type": "number", "default": 0.0, "description": "Edit start time."},
                "end_time": {"type": "number", "default": 0.0, "description": "Edit end time."},
                "transition": {
                    "type": "string",
                    "default": "cut",
                    "description": "Transition type (cut, fade, wipe, dissolve).",
                },
                "transition_duration": {"type": "number", "default": 0.5, "description": "Transition duration."},
                "color_grade": {"type": "string", "default": "none", "description": "Color grade."},
                "volume": {"type": "number", "default": 1.0, "description": "Volume level."},
                "root": {"type": "string"},
            },
            "required": ["project_id", "clip_id"],
        },
        "description": "Editor's cut decision for a clip — trim, transition, grade, volume for stitch/assembly.",
    },
}


def get_builtin_tools() -> list[tuple[str, ToolHandler, dict[str, Any], str]]:
    """Return the list of (name, handler, json_schema, description) tuples
    expected by ``agent_tool_loop`` in ``agnes_client``.

    The OpenAI-compatible ``tools`` payload requires:
        {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
    so each entry is pre-shaped to drop in as-is.
    """
    out: list[tuple[str, ToolHandler, dict[str, Any], str]] = []
    for name, spec in BUILTIN_TOOLS.items():
        out.append((name, spec["handler"], spec["schema"], spec["description"]))
    return out


def describe_tools() -> dict[str, Any]:
    """Human-readable summary of the built-in tool set, for CLI help."""
    return {
        name: {
            "description": spec["description"],
            "parameters": spec["schema"],
        }
        for name, spec in BUILTIN_TOOLS.items()
    }


def invoke_tool(tool_name: str, **kwargs: Any) -> Any:
    """Invoke a named built-in tool with keyword args.

    Returns the raw handler result (dict, list, str, …). Callers in
    ``agent_tool_loop`` will JSON-stringify non-string results.
    """
    if tool_name not in BUILTIN_TOOLS:
        raise KeyError(f"Unknown tool: {tool_name}. Available: {list(BUILTIN_TOOLS)}")
    handler = BUILTIN_TOOLS[tool_name]["handler"]
    return handler(**kwargs)

