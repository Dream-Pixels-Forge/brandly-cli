"""Review queue routes (issue #127): queue, approve, reject, media preview."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from brandly_cli.web import deps, review

router = APIRouter(prefix="/api/projects/{project_id}/review", tags=["review"])


@router.get("/queue", response_model=dict)
async def get_queue(
    project_id: str,
    request: Request,
    stage: str | None = None,
    scene: int | None = None,
    below_threshold: int | None = None,
) -> dict:
    """Everything that auto-approved since the last human review session."""
    root = request.app.state.root
    return review.queue(
        root,
        project_id,
        stage=stage,
        scene=scene,
        below_threshold=below_threshold,
    )


def _reviewer(body: dict[str, Any]) -> str:
    reviewer = str(body.get("reviewer") or "").strip()
    return reviewer or "web-reviewer"


@router.post("/{item_id}/approve", response_model=dict)
async def approve_item(project_id: str, item_id: str, body: dict, request: Request) -> dict:
    """Approve: stamp reviewer + timestamp into the generation record."""
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    return review.approve(root, project_id, item_id, reviewer=_reviewer(body))


@router.post("/{item_id}/reject", response_model=dict)
async def reject_item(project_id: str, item_id: str, body: dict, request: Request) -> dict:
    """Reject: write the review note, un-flag the shot for a re-run."""
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    note = str(body.get("note") or "").strip()
    return review.reject(
        root,
        project_id,
        item_id,
        note=note,
        reviewer=_reviewer(body),
    )


@router.get("/{item_id}/media")
async def item_media(project_id: str, item_id: str, request: Request) -> Any:
    """Stream a queued item's media file (resolved through the queue only)."""
    root = request.app.state.root
    media = review.media_file(root, project_id, item_id)
    return FileResponse(str(media))
