"""Pipeline tools — job polling, timeline, gate, clip updates.

Tools map to skills:

* ``produce``, ``job_poll`` → ``brandly-video-generation``
* ``stitch``, ``update_clip``, ``reorder_timeline`` → ``dpf-senior-editor``
* ``export_platforms`` → ``brandly-film-collaborator``
* ``run_gate`` → ``brandly-film-critic-scorer``
* ``approve`` → ``brandly-film-collaborator``
* ``record_cost``, ``memory`` → ``brandly-init``

CLI-backed tools (produce, stitch, export_platforms, job_poll, approve,
record_cost, memory) live in ``agent_surface.CLI_TOOLS``; this module holds
the in-process library handlers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brandly_cli.agnes_client import list_jobs as _agnes_list_jobs
from brandly_cli.async_compat import run_async

# ---------------------------------------------------------------------------
# Tool: list_jobs
# ---------------------------------------------------------------------------

def _list_jobs(
    status: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """List recent Agnes video-generation jobs (read-only)."""
    try:
        return {"jobs": run_async(_agnes_list_jobs(status=status, limit=limit))}
    except Exception as e:
        return {"error": f"list_jobs: {e}"}


# ---------------------------------------------------------------------------
# Tool: get_timeline
# ---------------------------------------------------------------------------

def _get_timeline(
    project_id: str,
    root: str | None = None,
) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Tool: update_clip
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tool: reorder_timeline
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tool: run_gate
# ---------------------------------------------------------------------------

def _run_gate(
    project_id: str,
    clip_id: str,
    root: str | None = None,
) -> dict[str, Any]:
    """Run the deterministic quality gate on a clip (no AI, offline)."""
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
# Tool registry — pipeline domain
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
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
}
