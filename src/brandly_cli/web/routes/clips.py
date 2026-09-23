"""Clip mutation routes (update, regenerate)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from brandly_cli.constants import DEFAULT_AGNES_VIDEO_MODEL
from brandly_cli.web import deps
from brandly_cli.web.models import ClipRegenerateResponse, ClipResponse, ClipUpdate
from brandly_cli.web.state import MAX_CLIP_DURATION, MIN_CLIP_DURATION, TimelineState

router = APIRouter(prefix="/api/projects/{project_id}", tags=["clips"])


@router.patch("/clips/{clip_id}", response_model=dict)
async def patch_clip(
    project_id: str,
    clip_id: str,
    body: dict,
    request: Request,
) -> dict:
    """Update a single clip field."""
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    state = TimelineState(project_id, root)
    if state.get_clip(clip_id) is None:
        raise HTTPException(status_code=404, detail=f"Clip not found: {clip_id}")

    updated = state.update_clip(clip_id, ClipUpdate(**body))
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to update clip")

    return ClipResponse(clip=updated).model_dump()


@router.post("/clips/{clip_id}/regenerate", response_model=dict)
async def regenerate_clip(
    project_id: str,
    clip_id: str,
    request: Request,
) -> dict:
    """Regenerate a single clip via AI video generation."""
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    state = TimelineState(project_id, root)
    clip = state.get_clip(clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail=f"Clip not found: {clip_id}")

    # Mark as generating
    state.regenerate_clip_status(clip_id, "generating")

    # Get project config
    project_json = Path(root) / ".brandly" / project_id / "project.json"

    try:
        import json as _json
        proj_data = _json.loads(project_json.read_text(encoding="utf-8"))
    except Exception:
        proj_data = {}

    aspect_ratio = proj_data.get("aspect_ratio", "16:9")
    duration = int(max(MIN_CLIP_DURATION, min(MAX_CLIP_DURATION, clip.duration)))

    # Build the generation call — import here so tests can patch the provider
    from brandly_cli.agnes_client import create_video_task, poll_video

    try:
        task = await create_video_task(
            prompt=clip.prompt,
            model=DEFAULT_AGNES_VIDEO_MODEL,
            duration=duration,
            aspect_ratio=aspect_ratio,
        )

        job_id = task.get("video_id") or task.get("id")
        if not job_id:
            state.regenerate_clip_status(clip_id, "failed")
            return ClipRegenerateResponse(
                clip_id=clip_id,
                status="failed",
                error="No job ID returned from API",
            ).model_dump()

        # Poll for completion
        result = await poll_video(job_id, max_wait_seconds=300, interval_seconds=5)

        if result.get("status") == "completed" and result.get("video_path"):
            video_path = Path(result["video_path"])
            rel_path = f"videos/scenes/{video_path.name}"
            state.set_clip_file(clip_id, rel_path)
            return ClipRegenerateResponse(
                clip_id=clip_id,
                status="completed",
                file_path=rel_path,
            ).model_dump()
        else:
            state.regenerate_clip_status(clip_id, "failed")
            return ClipRegenerateResponse(
                clip_id=clip_id,
                status="failed",
                error=result.get("error", "Generation failed"),
            ).model_dump()

    except Exception as e:
        state.regenerate_clip_status(clip_id, "failed")
        return ClipRegenerateResponse(
            clip_id=clip_id,
            status="failed",
            error=str(e),
        ).model_dump()
