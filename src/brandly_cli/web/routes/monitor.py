"""Production monitor routes (issue #126): snapshot + live progress tail."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from brandly_cli.web import deps, monitor

router = APIRouter(prefix="/api/projects/{project_id}", tags=["monitor"])


@router.get("/monitor", response_model=dict)
async def monitor_snapshot(project_id: str, request: Request) -> dict:
    """Full monitor snapshot: per-shot rows, gate scores, provider health."""
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    return monitor.snapshot(root, project_id)


@router.get("/monitor/tail", response_model=dict)
async def monitor_tail(
    project_id: str,
    request: Request,
    stage: str = Query("produce"),
    offset: int = Query(0, ge=0),
) -> dict:
    """Progress-log lines after ``offset`` (the poll fallback for the ws tail).

    ``stage`` selects a fixed filename from ``monitor.STAGES`` — it is never
    joined into a path, so it cannot address anything outside the two logs.
    """
    root = request.app.state.root
    deps.require_project_dir(root, project_id)
    if stage not in monitor.STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stage {stage!r} — expected one of {', '.join(monitor.STAGES)}",
        )
    return monitor.tail(root, project_id, stage, offset)
