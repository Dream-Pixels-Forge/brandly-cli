"""Timeline CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from brandly_cli.web import deps
from brandly_cli.web.models import (
    TimelinePatch,
    TimelineResponse,
)
from brandly_cli.web.state import TimelineState

router = APIRouter(prefix="/api/projects/{project_id}", tags=["timeline"])


@router.get("/timeline", response_model=dict)
async def get_timeline(project_id: str, request: Request) -> dict:
    """Get the timeline for an existing project."""
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    try:
        timeline = TimelineState(project_id, root).load()
        return TimelineResponse(timeline=timeline).model_dump()
    except Exception as e:
        return TimelineResponse(error=str(e)).model_dump()


@router.put("/timeline", response_model=dict)
async def put_timeline(project_id: str, patch: TimelinePatch, request: Request) -> dict:
    """Replace the entire timeline (durations clamped by ``TimelineState``)."""
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    try:
        state = TimelineState(project_id, root)
        state.load()
        state.replace_clips(patch.clips)
        if patch.color_grade:
            state.set_color_grade(patch.color_grade)
        return TimelineResponse(timeline=state.timeline).model_dump()
    except Exception as e:
        return TimelineResponse(error=str(e)).model_dump()
