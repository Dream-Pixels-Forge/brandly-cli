"""Quality gate endpoint — deterministic pre-check on a clip."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from brandly_cli.web import deps
from brandly_cli.web.state import TimelineState

router = APIRouter(prefix="/api/projects/{project_id}", tags=["gate"])


@router.post("/clips/{clip_id}/gate", response_model=dict)
async def run_gate(project_id: str, clip_id: str, request: Request) -> dict:
    """Run the deterministic quality gate on a clip and persist the result."""
    root = request.app.state.root
    proj_dir, media = deps.require_clip_media(root, project_id, clip_id)

    state = TimelineState(project_id, root)
    clip = state.get_clip(clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail=f"Clip not found: {clip_id}")

    if not media.is_file():
        raise HTTPException(status_code=404, detail=f"Clip file not found: {clip_id}")

    from brandly_cli.quality_gate import PASS, verify_element

    try:
        result = await verify_element(
            media,
            use_ai=False,
            root=root,
            project_id=project_id,
            write_report=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality gate failed: {e}") from e

    status = result.status  # "pass", "warn", or "fail"
    score = result.score

    # Persist status unless it's already pass (no-op write)
    if status != PASS:
        clip_obj = state.get_clip(clip_id)
        if clip_obj:
            clip_obj.quality_status = status
            from brandly_cli.web.state import _now_iso
            clip_obj.updated_at = _now_iso()
            state.save()

    return {"status": status, "score": score}
