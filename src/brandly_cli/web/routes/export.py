"""Export/stitch routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from brandly_cli.web import deps
from brandly_cli.web.models import ExportResult
from brandly_cli.web.state import TimelineState

router = APIRouter(prefix="/api/projects/{project_id}", tags=["export"])


@router.post("/export", response_model=dict)
async def export_project(project_id: str, request: Request) -> dict:
    """Stitch all clips in the timeline into a final video."""
    root = request.app.state.root
    proj_dir = deps.require_project_dir(root, project_id)
    timeline = TimelineState(project_id, root).load()

    if not timeline.clips:
        raise HTTPException(status_code=400, detail="No clips in timeline")

    # Resolve clip paths (containment enforced by deps.clip_media_path)
    clips: list[Path] = []
    missing = []
    for clip in timeline.clips:
        clip_path = deps.clip_media_path(proj_dir, clip)
        if clip_path is not None:
            clips.append(clip_path)
        else:
            missing.append(clip.clip_path)

    if missing:
        return ExportResult(
            output_path="",
            duration_seconds=0.0,
            file_size_bytes=0,
            error=f"Missing clips: {', '.join(missing)}",
        ).model_dump()

    # Determine transition from first clip
    transition = "fade"
    if timeline.clips:
        t = timeline.clips[0].transition_in
        if t:
            transition = t

    # Export to projects/export/
    output_dir = proj_dir / "export"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{project_id}_stitched.mp4"

    try:
        from brandly_cli.stitch import stitch_videos

        result = await stitch_videos(
            clips=clips,
            output=output_path,
            transition=transition,
            transition_duration=timeline.clips[0].transition_duration if timeline.clips else 0.5,
            color_grade=timeline.color_grade,
            root=Path(root),
        )

        if "error" in result:
            return ExportResult(
                output_path="",
                duration_seconds=0.0,
                file_size_bytes=0,
                error=result["error"],
            ).model_dump()

        file_size = output_path.stat().st_size if output_path.exists() else 0
        return ExportResult(
            output_path=str(output_path),
            duration_seconds=result.get("duration_seconds", 0.0),
            file_size_bytes=file_size,
        ).model_dump()

    except Exception as e:
        return ExportResult(
            output_path="",
            duration_seconds=0.0,
            file_size_bytes=0,
            error=str(e),
        ).model_dump()
