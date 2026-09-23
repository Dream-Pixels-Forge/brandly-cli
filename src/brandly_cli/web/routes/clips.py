"""Clip mutation routes (update, regenerate)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from brandly_cli import layout
from brandly_cli.constants import DEFAULT_AGNES_VIDEO_MODEL, VIDEO_MODEL_INFO
from brandly_cli.cost_tracker import CostTracker, record_media_spend
from brandly_cli.io import download_file
from brandly_cli.planning import (
    upsert_production_plan,
    write_generation_doc,
    write_generation_plan,
)
from brandly_cli.style_presets import apply_style_preset
from brandly_cli.web import deps
from brandly_cli.web.models import ClipRegenerateResponse, ClipResponse, ClipUpdate
from brandly_cli.web.state import MAX_CLIP_DURATION, MIN_CLIP_DURATION, TimelineState

router = APIRouter(prefix="/api/projects/{project_id}", tags=["clips"])


def _mark_plan_failed(
    root: Path, project_id: str, plan: Path, model: str, clip_id: str
) -> None:
    """Mark the generation plan row FAILED without masking the real error."""
    try:
        upsert_production_plan(
            project_id,
            root=root,
            plan_file=str(plan),
            asset_type="video",
            model=model,
            status="FAILED",
            source="brandly timeline",
            shot_id=clip_id,
        )
    except Exception:
        pass  # plan bookkeeping must never hide the actual failure


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
    """Regenerate a clip, wired to the CLI's plan, budget and artifact paths."""
    root = request.app.state.root
    proj_dir = deps.require_project_dir(root, project_id)
    state = TimelineState(project_id, root)
    clip = state.get_clip(clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail=f"Clip not found: {clip_id}")

    model = DEFAULT_AGNES_VIDEO_MODEL
    cost = int(VIDEO_MODEL_INFO.get(model, {}).get("cost_credits", 0) or 0)  # type: ignore[call-overload]
    duration = int(max(MIN_CLIP_DURATION, min(MAX_CLIP_DURATION, clip.duration)))

    # Budget gate: refuse BEFORE spending. No cost.json yet means the project
    # has never spent — allow it (record_media_spend seeds it from project.json).
    if cost and (proj_dir / "cost.json").exists():
        afford = await CostTracker(root / ".brandly").can_afford(project_id, cost)
        if not afford["allowed"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Budget exceeded: {afford['remaining']} credits remaining, "
                    f"{cost} needed for {model}"
                ),
            )

    # Register the generation plan row now — it starts PENDING (plan line 61)
    # and is flipped to COMPLETED/FAILED by write_generation_doc / _mark_plan_failed.
    plan, _reused = write_generation_plan(
        project_id,
        "video",
        root=root,
        prompt=clip.prompt,
        model=model,
        style=clip.style,
        extra_config={"duration": f"{duration}s", "clip_id": clip.id},
        source="brandly timeline",
        shot_id=clip.id,
    )

    state.regenerate_clip_status(clip_id, "generating")

    try:
        import json as _json
        proj_data = _json.loads((proj_dir / "project.json").read_text(encoding="utf-8"))
    except Exception:
        proj_data = {}
    aspect_ratio = proj_data.get("aspect_ratio", "16:9")

    # Style presets are applied by the caller (providers stay dumb), using the
    # same rule as `brandly video`: the cinematic preset for cinematic clips.
    prompt = (
        apply_style_preset(clip.prompt, "cinematic")
        if clip.style == "cinematic"
        else clip.prompt
    )

    from brandly_cli.agnes_client import create_video_task, poll_video

    async def _broadcast(msg: dict) -> None:
        from brandly_cli.web.websocket import broadcast
        await broadcast(project_id, {"clip_id": clip_id, **msg})

    try:
        await _broadcast({"type": "generation_progress", "phase": "starting"})
        task = await create_video_task(
            prompt=prompt,
            model=model,
            duration=duration,
            aspect_ratio=aspect_ratio,
        )

        job_id = task.get("video_id") or task.get("id")
        if not job_id:
            state.regenerate_clip_status(clip_id, "failed")
            _mark_plan_failed(root, project_id, plan, model, clip_id)
            return ClipRegenerateResponse(
                clip_id=clip_id,
                status="failed",
                error="No job ID returned from API",
            ).model_dump()

        # poll_video returns a remote `url`, never a local `video_path` — so
        # download the finished clip into the project's videos/scenes/ folder.
        result = await poll_video(
            job_id, max_wait_seconds=300, interval_seconds=5, model_name=model
        )
        await _broadcast({"type": "generation_progress", "phase": "done"})
        url = result.get("url") or ""
        if result.get("status") == "completed" and url:
            filename = Path(clip.clip_path).name if clip.clip_path else f"{clip.id}.mp4"
            dest = layout.media_dir(proj_dir, "videos", "scenes") / filename
            await download_file(url, dest)
            rel_path = f"videos/scenes/{filename}"
            state.set_clip_file(clip_id, rel_path)

            # record_media_spend runs asyncio.run() internally, so offload it to
            # a worker thread — calling it in this running loop would raise.
            await asyncio.to_thread(record_media_spend, root, project_id, "video", model)

            # Writes the generation doc and flips the plan row to COMPLETED.
            write_generation_doc(
                project_id,
                "video",
                dest,
                root=root,
                prompt=prompt,
                model=model,
                style=clip.style,
                source="brandly timeline",
                plan_file=str(plan),
                metadata={"clip_id": clip_id, "video_id": job_id},
            )
            await _broadcast({"type": "generation_complete"})
            return ClipRegenerateResponse(
                clip_id=clip_id,
                status="completed",
                file_path=rel_path,
            ).model_dump()

        await _broadcast({"type": "generation_error", "error": result.get("error", "Generation failed")})
        state.regenerate_clip_status(clip_id, "failed")
        _mark_plan_failed(root, project_id, plan, model, clip_id)
        return ClipRegenerateResponse(
            clip_id=clip_id,
            status="failed",
            error=result.get("error", "Generation failed"),
        ).model_dump()

    except Exception as e:
        await _broadcast({"type": "generation_error", "error": str(e)})
        state.regenerate_clip_status(clip_id, "failed")
        _mark_plan_failed(root, project_id, plan, model, clip_id)
        return ClipRegenerateResponse(
            clip_id=clip_id,
            status="failed",
            error=str(e),
        ).model_dump()
